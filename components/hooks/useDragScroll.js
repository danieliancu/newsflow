import { useEffect } from 'react';

export function useDragScroll(ref) {
  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    let isDown = false;
    let startX = 0;
    let scrollLeft = 0;

    const mouseDownHandler = (e) => {
      isDown = true;
      element.classList.add('active'); // stilizează clasa "active" în CSS (ex: cursor: grabbing)
      startX = e.pageX - element.offsetLeft;
      scrollLeft = element.scrollLeft;
    };

    const mouseLeaveHandler = () => {
      isDown = false;
      element.classList.remove('active');
    };

    const mouseUpHandler = () => {
      isDown = false;
      element.classList.remove('active');
    };

    const mouseMoveHandler = (e) => {
      if (!isDown) return;
      e.preventDefault();
      const x = e.pageX - element.offsetLeft;
      const walk = (x - startX) * 2; // ajustează viteza de scroll după preferințe
      element.scrollLeft = scrollLeft - walk;
    };

    element.addEventListener('mousedown', mouseDownHandler);
    element.addEventListener('mouseleave', mouseLeaveHandler);
    element.addEventListener('mouseup', mouseUpHandler);
    element.addEventListener('mousemove', mouseMoveHandler);

    return () => {
      element.removeEventListener('mousedown', mouseDownHandler);
      element.removeEventListener('mouseleave', mouseLeaveHandler);
      element.removeEventListener('mouseup', mouseUpHandler);
      element.removeEventListener('mousemove', mouseMoveHandler);
    };
  }, [ref]);
}
