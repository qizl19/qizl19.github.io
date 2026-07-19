(function () {
  'use strict';

  const CELL_SIZE = 12;
  const CELL_GAP = 3;
  const REQUEST_TIMEOUT = 12000;
  const MONTH_NAMES = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'];

  function parseUtcDate(value) {
    const parts = value.split('-').map(Number);
    return new Date(Date.UTC(parts[0], parts[1] - 1, parts[2]));
  }

  function contributionTotal(total, contributions) {
    if (typeof total === 'number') return total;
    if (total && typeof total.lastYear === 'number') return total.lastYear;
    return contributions.reduce(function (sum, day) {
      return sum + (Number(day.count) || 0);
    }, 0);
  }

  function renderCalendar(card, payload) {
    const contributions = payload.contributions.slice().sort(function (a, b) {
      return a.date.localeCompare(b.date);
    });
    if (!contributions.length) throw new Error('贡献数据为空');

    const grid = card.querySelector('#github-calendar-grid');
    const months = card.querySelector('#github-calendar-months');
    const summary = card.querySelector('#github-calendar-summary');
    const status = card.querySelector('#github-calendar-status');
    const firstDate = parseUtcDate(contributions[0].date);
    const leadingDays = firstDate.getUTCDay();
    const weeks = Math.ceil((leadingDays + contributions.length) / 7);

    grid.innerHTML = '';
    grid.style.setProperty('--github-calendar-weeks', String(weeks));
    for (let index = 0; index < leadingDays; index += 1) {
      const spacer = document.createElement('span');
      spacer.className = 'github-calendar-cell is-empty';
      spacer.setAttribute('aria-hidden', 'true');
      grid.appendChild(spacer);
    }

    contributions.forEach(function (day) {
      const cell = document.createElement('span');
      const count = Number(day.count) || 0;
      const level = Math.max(0, Math.min(4, Number(day.level) || 0));
      const label = day.date + '：' + count + ' 次贡献';
      cell.className = 'github-calendar-cell';
      cell.dataset.level = String(level);
      cell.title = label;
      cell.setAttribute('aria-label', label);
      grid.appendChild(cell);
    });

    months.innerHTML = '';
    months.style.width = (weeks * (CELL_SIZE + CELL_GAP) - CELL_GAP) + 'px';
    let previousMonth = -1;
    contributions.forEach(function (day, index) {
      const date = parseUtcDate(day.date);
      const month = date.getUTCMonth();
      if (month === previousMonth || date.getUTCDate() > 7) return;
      previousMonth = month;
      const label = document.createElement('span');
      label.textContent = MONTH_NAMES[month];
      label.style.left = (Math.floor((leadingDays + index) / 7) * (CELL_SIZE + CELL_GAP)) + 'px';
      months.appendChild(label);
    });

    const total = contributionTotal(payload.total, contributions);
    summary.textContent = total + ' 次贡献 · 过去一年';
    status.textContent = contributions[0].date + ' 至 ' + contributions[contributions.length - 1].date;
    grid.setAttribute('aria-label', '过去一年共 ' + total + ' 次 GitHub 贡献；每个方格可查看每日贡献数');
    card.dataset.state = 'ready';
  }

  function renderFailure(card) {
    const summary = card.querySelector('#github-calendar-summary');
    const status = card.querySelector('#github-calendar-status');
    const user = card.dataset.user;
    summary.textContent = '暂时无法加载贡献数据';
    status.innerHTML = '<a href="https://github.com/' + encodeURIComponent(user) + '" target="_blank" rel="noopener noreferrer">前往 GitHub 查看</a>';
    card.dataset.state = 'error';
  }

  function initCalendar() {
    const card = document.getElementById('github-contributions');
    if (!card || card.dataset.state === 'loading' || card.dataset.state === 'ready') return;
    card.dataset.state = 'loading';

    const controller = new AbortController();
    const timeout = window.setTimeout(function () { controller.abort(); }, REQUEST_TIMEOUT);
    fetch(card.dataset.api, { signal: controller.signal, headers: { Accept: 'application/json' } })
      .then(function (response) {
        if (!response.ok) throw new Error('HTTP ' + response.status);
        return response.json();
      })
      .then(function (payload) {
        if (!payload || !Array.isArray(payload.contributions)) throw new Error('无效的贡献数据');
        renderCalendar(card, payload);
      })
      .catch(function () { renderFailure(card); })
      .finally(function () { window.clearTimeout(timeout); });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initCalendar, { once: true });
  } else {
    initCalendar();
  }
  document.addEventListener('pjax:complete', initCalendar);
}());
