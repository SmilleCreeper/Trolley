from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import urllib.request
import subprocess
import threading
import socket
import time
import json
import os
import sys
import traceback
import atexit
import tempfile
import shutil
import uuid
import ctypes
from ctypes import wintypes

class JobObject:
    def __init__(self):
        self.handle = None
        if sys.platform != 'win32':
            return
        self.handle = ctypes.windll.kernel32.CreateJobObjectW(None, None)
        if not self.handle:
            err = ctypes.GetLastError()
            print(f'[server] CreateJobObjectW FAILED, error code {err}')
            return
        class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ('PerProcessUserTimeLimit', ctypes.c_int64),
                ('PerJobUserTimeLimit', ctypes.c_int64),
                ('LimitFlags', wintypes.DWORD),
                ('MinimumWorkingSetSize', ctypes.c_size_t),
                ('MaximumWorkingSetSize', ctypes.c_size_t),
                ('ActiveProcessLimit', wintypes.DWORD),
                ('Affinity', ctypes.c_size_t),
                ('PriorityClass', wintypes.DWORD),
                ('SchedulingClass', wintypes.DWORD),
            ]
        class IO_COUNTERS(ctypes.Structure):
            _fields_ = [
                ('ReadOperationCount', ctypes.c_uint64),
                ('WriteOperationCount', ctypes.c_uint64),
                ('OtherOperationCount', ctypes.c_uint64),
                ('ReadTransferCount', ctypes.c_uint64),
                ('WriteTransferCount', ctypes.c_uint64),
                ('OtherTransferCount', ctypes.c_uint64),
            ]
        class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ('BasicLimitInformation', JOBOBJECT_BASIC_LIMIT_INFORMATION),
                ('IoInfo', IO_COUNTERS),
                ('ProcessMemoryLimit', ctypes.c_size_t),
                ('JobMemoryLimit', ctypes.c_size_t),
                ('PeakProcessMemoryUsed', ctypes.c_size_t),
                ('PeakJobMemoryUsed', ctypes.c_size_t),
            ]
        JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
        JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK = 0x00000800
        JobObjectExtendedLimitInformation = 9
        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.LimitFlags = (
            JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK
        )
        ok = ctypes.windll.kernel32.SetInformationJobObject(
            self.handle, JobObjectExtendedLimitInformation,
            ctypes.byref(info), ctypes.sizeof(info)
        )
        if not ok:
            err = ctypes.GetLastError()
            print(f'[server] SetInformationJobObject FAILED, error code {err}')
    def assign(self, proc):
        if not self.handle:
            return
        h_process = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, proc.pid)
        if not h_process:
            err = ctypes.GetLastError()
            print(f'[server] OpenProcess FAILED for pid {proc.pid}, error code {err}')
            return
        ok = ctypes.windll.kernel32.AssignProcessToJobObject(self.handle, h_process)
        if not ok:
            err = ctypes.GetLastError()
            print(f'[server] AssignProcessToJobObject FAILED for pid {proc.pid}, error code {err}')
        else:
            print(f'[server] Assigned pid {proc.pid} to job object')
        ctypes.windll.kernel32.CloseHandle(h_process)
    def close(self):
        if self.handle:
            ctypes.windll.kernel32.CloseHandle(self.handle)
            self.handle = None

ELECTRON_PORT = 5051
MY_PORT = 5050
HEARTBEAT_INTERVAL = 1
REQUEST_TIMEOUT = 2

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
subprocs = []
job = JobObject()
jobs_lock = threading.Lock()
jobs = {}

def kill_subprocs():
    for proc in subprocs[:]:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
                proc.wait(timeout=3)
            except Exception:
                pass
    subprocs.clear()
    job.close()

atexit.register(kill_subprocs)

def _run_job(job_id, script_path, output_path, progress_path, temp_dir):
    try:
        proc = subprocess.Popen(
            [sys.executable, script_path, '--output', output_path, '--progress', progress_path],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        with jobs_lock:
            if job_id in jobs:
                jobs[job_id]['proc'] = proc
        proc.wait(timeout=120)
        if proc.returncode != 0:
            raise Exception(f'Script exited with code {proc.returncode}')
        with open(output_path, 'r') as f:
            result = json.load(f)
        with jobs_lock:
            if job_id in jobs:
                jobs[job_id]['result'] = result
                jobs[job_id]['done'] = True
    except Exception as e:
        with jobs_lock:
            if job_id in jobs:
                jobs[job_id]['error'] = str(e)
                jobs[job_id]['done'] = True
    def cleanup():
        time.sleep(30)
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass
        with jobs_lock:
            jobs.pop(job_id, None)
    threading.Thread(target=cleanup, daemon=True).start()

class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()
    def do_GET(self):
        if self.path == '/heartbeat':
            self.send_response(200)
            self._cors()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        elif self.path.startswith('/status/'):
            job_id = self.path.split('/')[-1]
            with jobs_lock:
                entry = jobs.get(job_id)
            if not entry:
                self.send_response(404)
                self._cors()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'job not found'}).encode())
                return
            self.send_response(200)
            self._cors()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            if entry['done']:
                if entry['error']:
                    resp = {'done': True, 'error': entry['error']}
                else:
                    resp = {'done': True, 'result': entry['result']}
            else:
                resp = {'done': False, 'percent': 0, 'message': ''}
                try:
                    with open(os.path.join(entry['temp_dir'], 'progress.json'), 'r') as f:
                        prog = json.load(f)
                        resp['percent'] = prog.get('percent', 0)
                        resp['message'] = prog.get('message', '')
                except Exception:
                    pass
            self.wfile.write(json.dumps(resp).encode())
        else:
            self.send_response(404)
            self._cors()
            self.end_headers()
    def do_POST(self):
        if self.path == '/run':
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length))
            script = body.get('script', '')
            script_path = os.path.join(BASE_DIR, 'server', 'python', os.path.basename(script))
            if not os.path.isfile(script_path):
                self.send_response(404)
                self._cors()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'script not found'}).encode())
                return
            job_id = uuid.uuid4().hex[:8]
            temp_dir = tempfile.mkdtemp(prefix=f'job_{job_id}_')
            output_path = os.path.join(temp_dir, 'output.json')
            progress_path = os.path.join(temp_dir, 'progress.json')
            with jobs_lock:
                jobs[job_id] = {'done': False, 'result': None, 'error': None, 'temp_dir': temp_dir, 'proc': None}
            threading.Thread(target=_run_job, args=(job_id, script_path, output_path, progress_path, temp_dir), daemon=True).start()
            self.send_response(202)
            self._cors()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'job_id': job_id}).encode())
        else:
            self.send_response(404)
            self._cors()
            self.end_headers()
    def log_message(self, format, *args):
        pass

def check_electron():
    time.sleep(3)
    url = f'http://localhost:{ELECTRON_PORT}/heartbeat'
    misses = 0
    while True:
        time.sleep(HEARTBEAT_INTERVAL)
        try:
            req = urllib.request.Request(url)
            urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT)
            misses = 0
        except Exception:
            misses += 1
            if misses >= 3:
                print('[server] Electron heartbeat failed, shutting down')
                kill_subprocs()
                os._exit(1)

def start():
    server = ThreadingHTTPServer(('localhost', MY_PORT), Handler)
    thread = threading.Thread(target=check_electron, daemon=True)
    thread.start()
    print(f'[server] Python heartbeat server on port {MY_PORT}')
    server.serve_forever()

if __name__ == '__main__':
    start()
