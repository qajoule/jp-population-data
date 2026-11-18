(() => {
  const circleSelector = 'circle[data-csv-year][data-csv-series-id][data-csv-metric]';
  const readAttribute = (element, name) => element.getAttribute(`data-csv-${name}`) ?? '';
  const decimalPlaces = (value) => (value.split('.')[1] ?? '').length;
  const labelFor = (circle) => readAttribute(circle, 'series-label') || readAttribute(circle, 'series-id');
  const readout = document.createElement('aside');
  readout.className = 'figure-readout';
  readout.hidden = true;
  readout.setAttribute('aria-live', 'polite');
  readout.setAttribute('role', 'status');
  document.body.append(readout);

  const render = (plot, year, points, formatter) => {
    readout.replaceChildren();
    const heading = document.createElement('p');
    heading.className = 'figure-readout__year';
    heading.textContent = `${year}年 - ${plot.dataset.readoutUnit ?? ''}`;
    const list = document.createElement('ul');
    points.forEach((point) => {
      const item = document.createElement('li');
      const label = document.createElement('span');
      label.textContent = labelFor(point);
      const value = document.createElement('span');
      value.textContent = formatter.format(Number(readAttribute(point, 'value')));
      item.append(label, value);
      list.append(item);
    });
    readout.append(heading, list);
    readout.hidden = false;
  };
  const reposition = (position) => {
    const margin = 8;
    const viewportWidth = window.visualViewport?.width ?? document.documentElement.clientWidth;
    const viewportHeight = window.visualViewport?.height ?? document.documentElement.clientHeight;
    const maxX = Math.max(margin, viewportWidth - readout.offsetWidth - margin);
    const maxY = Math.max(margin, viewportHeight - readout.offsetHeight - margin);
    const x = Math.min(Math.max(margin, position.x + 14), maxX);
    const y = Math.min(Math.max(margin, position.y + 14), maxY);
    readout.style.left = `${x}px`;
    readout.style.top = `${y}px`;
  };
  const hide = () => { readout.hidden = true; };
  const setActiveYear = (svg, points) => {
    svg.querySelectorAll(`${circleSelector}.is-active`).forEach((circle) => circle.classList.remove('is-active'));
    points.forEach((circle) => circle.classList.add('is-active'));
    const guide = svg.querySelector('.figure-focus-guide');
    const point = points[0];
    if (!guide || !point) return;
    const x = point.getAttribute('cx');
    if (!x) return;
    guide.querySelector('line')?.setAttribute('x1', x);
    guide.querySelector('line')?.setAttribute('x2', x);
    guide.removeAttribute('display');
  };
  const clearActiveYear = (svg) => {
    svg.querySelectorAll(`${circleSelector}.is-active`).forEach((circle) => circle.classList.remove('is-active'));
    svg.querySelector('.figure-focus-guide')?.setAttribute('display', 'none');
  };
  let activeTouchSelection = null;
  let visibleSvg = null;
  const dismissTouchReadout = () => {
    if (!activeTouchSelection) return false;
    activeTouchSelection();
    activeTouchSelection = null;
    hide();
    return true;
  };

  document.addEventListener('pointerdown', dismissTouchReadout, true);
  document.addEventListener('pointermove', (event) => {
    if (event.pointerType !== 'touch' && dismissTouchReadout()) event.stopPropagation();
  }, true);
  document.addEventListener('wheel', dismissTouchReadout, true);
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && visibleSvg && !readout.hidden) {
      clearActiveYear(visibleSvg);
      activeTouchSelection = null;
      hide();
      return;
    }
    if (dismissTouchReadout()) event.stopPropagation();
  }, true);

  document.querySelectorAll('.plot[data-readout-unit]').forEach((plot) => {
    const svg = plot.querySelector('svg[data-figure-id]');
    if (!svg) return;
    const byYear = new Map();
    let precision = 0;
    for (const circle of svg.querySelectorAll(circleSelector)) {
      const year = readAttribute(circle, 'year');
      if (!byYear.has(year)) byYear.set(year, []);
      byYear.get(year).push(circle);
      precision = Math.min(2, Math.max(precision, decimalPlaces(readAttribute(circle, 'value'))));
    }
    const formatter = new Intl.NumberFormat('ja-JP', { minimumFractionDigits: precision, maximumFractionDigits: precision });
    const years = [...byYear.keys()].sort((left, right) => Number(left) - Number(right));
    const positions = years.map(year => ({ year, x: byYear.get(year)[0].cx.baseVal.value }));
    function nearestYear(clientX) {
      const matrix = svg.getScreenCTM();
      if (!matrix || !positions.length) return;
      const x = (clientX - matrix.e) / matrix.a;
      return positions.reduce((best, point) => Math.abs(point.x - x) < Math.abs(best.x - x) ? point : best).year;
    }
    const guide = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    guide.classList.add('figure-focus-guide');
    guide.setAttribute('aria-hidden', 'true');
    guide.setAttribute('display', 'none');
    const guideLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    guideLine.setAttribute('y1', svg.dataset.yScalePixelTop ?? '0');
    guideLine.setAttribute('y2', svg.dataset.yScalePixelBottom ?? svg.getAttribute('height') ?? '0');
    guide.append(guideLine);
    svg.append(guide);
    let currentYear = years[0];
    const showYear = (year, position) => {
      const points = byYear.get(year);
      if (!points) return;
      if (visibleSvg === svg && currentYear === year && !readout.hidden) {
        reposition(position);
        return;
      }
      if (visibleSvg && visibleSvg !== svg) clearActiveYear(visibleSvg);
      visibleSvg = svg;
      currentYear = year;
      setActiveYear(svg, points);
      render(plot, year, points, formatter);
      reposition(position);
    };
    svg.addEventListener('pointermove', (event) => {
      if (event.pointerType === 'touch') return;
      showYear(nearestYear(event.clientX), event);
    });
    const clearPointerSelection = (event) => {
      if (event.pointerType === 'touch') return;
      if (event.relatedTarget instanceof Node && plot.contains(event.relatedTarget)) return;
      clearActiveYear(svg);
      hide();
    };
    plot.addEventListener('pointerleave', clearPointerSelection);
    plot.addEventListener('pointerout', clearPointerSelection);
    svg.addEventListener('pointerup', (event) => {
      if (event.pointerType !== 'touch') return;
      showYear(nearestYear(event.clientX), event);
      activeTouchSelection = () => clearActiveYear(svg);
    });
    plot.addEventListener('focus', () => {
      const rect = plot.getBoundingClientRect();
      showYear(currentYear, { x: rect.right, y: rect.bottom });
    });
    plot.addEventListener('blur', () => {
      clearActiveYear(svg);
      hide();
    });
    plot.addEventListener('keydown', (event) => {
      const index = years.indexOf(currentYear);
      let nextYear;
      if (event.key === 'ArrowLeft') nextYear = years[Math.max(0, index - 1)];
      if (event.key === 'ArrowRight') nextYear = years[Math.min(years.length - 1, index + 1)];
      if (event.key === 'Home') nextYear = years[0];
      if (event.key === 'End') nextYear = years[years.length - 1];
      if (event.key === 'Escape') {
        clearActiveYear(svg);
        hide();
        return;
      }
      if (!nextYear) return;
      event.preventDefault();
      const rect = plot.getBoundingClientRect();
      showYear(nextYear, { x: rect.right, y: rect.bottom });
    });
  });
})();
