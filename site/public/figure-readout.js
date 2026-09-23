(() => {
  const circleSelector = 'circle[data-csv-year][data-csv-series-id][data-csv-metric]';
  const readAttribute = (element, name) => element.getAttribute(`data-csv-${name}`) ?? '';
  const decimalPlaces = (value) => (value.split('.')[1] ?? '').length;
  const precisionFor = (plot) => Math.min(2, Math.max(0, ...[...plot.querySelectorAll(circleSelector)]
    .map((circle) => decimalPlaces(readAttribute(circle, 'value')))));
  const formatValue = (value, precision) => new Intl.NumberFormat('ja-JP', {
    minimumFractionDigits: precision,
    maximumFractionDigits: precision,
  }).format(Number(value));
  const labelFor = (circle) => readAttribute(circle, 'series-label') || readAttribute(circle, 'series-id');
  const pointsForYear = (plot, year) => [...plot.querySelectorAll(circleSelector)]
    .filter((circle) => readAttribute(circle, 'year') === year);
  const readout = document.createElement('aside');
  readout.className = 'figure-readout';
  readout.hidden = true;
  readout.setAttribute('aria-live', 'polite');
  readout.setAttribute('role', 'status');
  document.body.append(readout);

  const show = (circle, position) => {
    const plot = circle.closest('.plot');
    const year = readAttribute(circle, 'year');
    if (!plot || !year) return;
    const points = pointsForYear(plot, year);
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
      value.textContent = formatValue(readAttribute(point, 'value'), precisionFor(plot));
      item.append(label, value);
      list.append(item);
    });
    readout.append(heading, list);
    readout.hidden = false;
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
  const setActiveYear = (svg, plot, year) => {
    svg.querySelectorAll(`${circleSelector}.is-active`).forEach((circle) => circle.classList.remove('is-active'));
    pointsForYear(plot, year).forEach((circle) => circle.classList.add('is-active'));
    const guide = svg.querySelector('.figure-focus-guide');
    const point = pointsForYear(plot, year)[0];
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
  const dismissTouchReadout = () => {
    if (!activeTouchSelection) return false;
    activeTouchSelection();
    activeTouchSelection = null;
    hide();
    return true;
  };
  const nearestCircle = (svg, clientX) => [...svg.querySelectorAll(circleSelector)]
    .reduce((nearest, circle) => {
      const distance = Math.abs(circle.getBoundingClientRect().x - clientX);
      return !nearest || distance < nearest.distance ? { circle, distance } : nearest;
    }, null)?.circle;

  document.addEventListener('pointerdown', dismissTouchReadout, true);
  document.addEventListener('pointermove', (event) => {
    if (event.pointerType !== 'touch' && dismissTouchReadout()) event.stopPropagation();
  }, true);
  document.addEventListener('wheel', dismissTouchReadout, true);
  document.addEventListener('keydown', (event) => {
    if (dismissTouchReadout()) event.stopPropagation();
  }, true);

  document.querySelectorAll('.plot[data-readout-unit]').forEach((plot) => {
    const svg = plot.querySelector('svg[data-figure-id]');
    if (!svg) return;
    const years = [...new Set([...svg.querySelectorAll(circleSelector)]
      .map((circle) => readAttribute(circle, 'year')))]
      .filter(Boolean)
      .sort((left, right) => Number(left) - Number(right));
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
      const circle = pointsForYear(plot, year)[0];
      if (!circle) return;
      currentYear = year;
      setActiveYear(svg, plot, year);
      show(circle, position);
    };
    svg.addEventListener('pointermove', (event) => {
      if (event.pointerType === 'touch') return;
      const circle = nearestCircle(svg, event.clientX);
      if (circle) {
        showYear(readAttribute(circle, 'year'), event);
      }
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
      const circle = nearestCircle(svg, event.clientX);
      if (!circle) return;
      showYear(readAttribute(circle, 'year'), event);
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
