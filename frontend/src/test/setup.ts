import '@testing-library/jest-dom';

// JSDOM mock for scrollIntoView
window.HTMLElement.prototype.scrollIntoView = window.HTMLElement.prototype.scrollIntoView || function () {};
