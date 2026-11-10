import styles from './RegionLabel.module.css';

function createLabelElement(label, onClick) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = [styles.label, styles[label.state]].filter(Boolean).join(' ');
  button.setAttribute('aria-label', `${label.name} 선택`);
  button.setAttribute('aria-pressed', String(label.state === 'selected'));
  button.disabled = label.state === 'dimmed';

  const dot = document.createElement('span');
  dot.className = styles.dot;
  dot.setAttribute('aria-hidden', 'true');
  const name = document.createElement('span');
  name.textContent = label.name;
  button.append(dot, name);

  const handleClick = () => onClick?.(label.code);
  button.addEventListener('click', handleClick);
  return { button, removeListener: () => button.removeEventListener('click', handleClick) };
}

// 지역 라벨을 CustomOverlay 로 그리고, 모두 지우는 함수를 돌려준다.
// 시·도 경계(폴리곤) 방식으로 바꿀 때는 이 함수만 교체한다.
export function renderRegionLabels(maps, map, labels, { onClick } = {}) {
  const rendered = labels.map((label) => {
    const { button, removeListener } = createLabelElement(label, onClick);
    const overlay = new maps.CustomOverlay({
      map,
      position: new maps.LatLng(label.lat, label.lng),
      content: button,
      xAnchor: 0.5,
      yAnchor: 0.5,
      zIndex: label.state === 'selected' ? 2 : 1,
      clickable: true,
    });
    return { overlay, removeListener };
  });

  return () => {
    rendered.forEach(({ overlay, removeListener }) => {
      removeListener();
      overlay.setMap(null);
    });
  };
}
