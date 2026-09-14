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
    const x = Math.min(position.x + 14, window.innerWidth - readout.offsetWidth - 8);
    const y = Math.min(position.y + 14, window.innerHeight - readout.offsetHeight - 8);
    readout.style.left = `${Math.max(8, x)}px`;
    readout.style.top = `${Math.max(8, y)}px`;
    readout.hidden = false;
  };
  const hide = () => { readout.hidden = true; };
  const nearestCircle = (svg, clientX) => [...svg.querySelectorAll(circleSelector)]
    .reduce((nearest, circle) => {
      const distance = Math.abs(circle.getBoundingClientRect().x - clientX);
      return !nearest || distance < nearest.distance ? { circle, distance } : nearest;
    }, null)?.circle;

  document.querySelectorAll('.plot[data-readout-unit]').forEach((plot) => {
    const svg = plot.querySelector('svg[data-figure-id]');
    if (!svg) return;
    const years = [...new Set([...svg.querySelectorAll(circleSelector)]
      .map((circle) => readAttribute(circle, 'year')))]
      .filter(Boolean)
      .sort((left, right) => Number(left) - Number(right));
    let currentYear = years[0];
    const showYear = (year, position) => {
      const circle = pointsForYear(plot, year)[0];
      if (!circle) return;
      currentYear = year;
      show(circle, position);
    };
    let longTouch;
    svg.addEventListener('pointermove', (event) => {
      if (event.pointerType === 'touch') return;
      const circle = nearestCircle(svg, event.clientX);
      if (circle) showYear(readAttribute(circle, 'year'), event);
    });
    svg.addEventListener('pointerleave', hide);
    svg.addEventListener('pointerdown', (event) => {
      if (event.pointerType !== 'touch') return;
      const circle = nearestCircle(svg, event.clientX);
      if (!circle) return;
      longTouch = window.setTimeout(() => showYear(readAttribute(circle, 'year'), event), 500);
    });
    svg.addEventListener('pointerup', () => window.clearTimeout(longTouch));
    svg.addEventListener('pointercancel', () => window.clearTimeout(longTouch));
    plot.addEventListener('focus', () => {
      const rect = plot.getBoundingClientRect();
      showYear(currentYear, { x: rect.right, y: rect.bottom });
    });
    plot.addEventListener('blur', hide);
    plot.addEventListener('keydown', (event) => {
      const index = years.indexOf(currentYear);
      let nextYear;
      if (event.key === 'ArrowLeft') nextYear = years[Math.max(0, index - 1)];
      if (event.key === 'ArrowRight') nextYear = years[Math.min(years.length - 1, index + 1)];
      if (event.key === 'Home') nextYear = years[0];
      if (event.key === 'End') nextYear = years[years.length - 1];
      if (event.key === 'Escape') {
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
