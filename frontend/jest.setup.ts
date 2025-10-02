import '@testing-library/jest-dom';
// Polyfill ResizeObserver for libraries like recharts in jsdom
class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
// @ts-ignore
global.ResizeObserver = ResizeObserver;


