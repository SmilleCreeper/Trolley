const ProgressBar = {
  _fill: null,
  _status: null,
  _prev: 0,
  _startTime: 0,
  _label: '',

  init() {
    this._fill = document.getElementById('titlebar-fill');
    this._status = document.getElementById('titlebar-status');
  },

  show(label) {
    this._label = label || '';
    this._prev = 0;
    this._startTime = Date.now();
    this._fill.style.width = '0%';
    this._fill.style.background = '#2a6b6b';
    this._fill.style.opacity = '1';
    this._status.style.opacity = '1';
    this.set(0);
  },

  _formatTime(ms) {
    const totalSec = Math.max(0, Math.round(ms / 1000));
    const min = Math.floor(totalSec / 60);
    const sec = totalSec % 60;
    return `${min}m ${sec.toString().padStart(2, '0')}s`;
  },

  _updateText(pct) {
    const elapsed = Date.now() - this._startTime;
    let eta = '';
    if (pct > 0) {
      const total = elapsed / (pct / 100);
      eta = this._formatTime(total - elapsed);
    } else {
      eta = '--';
    }
    this._status.textContent = `${this._label} | Estimated Time: ${eta}`;
  },

  set(percent, label) {
    const pct = Math.min(100, Math.max(0, percent));
    if (label !== undefined) this._label = label;
    if (pct > this._prev) {
      this._fill.style.background = '#388e3c';
    } else if (pct < this._prev) {
      this._fill.style.background = '#d32f2f';
    }
    this._fill.style.width = pct + '%';
    this._prev = pct;
    this._updateText(pct);
  },

  hide() {
    this._fill.style.opacity = '0';
    this._status.style.opacity = '0';
    setTimeout(() => {
      this._fill.style.width = '0%';
      this._prev = 0;
    }, 300);
  },
};
