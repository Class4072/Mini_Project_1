// Jest(babel-jest) 전용. Vite 빌드는 @vitejs/plugin-react 가 처리하므로 이 설정을 쓰지 않는다.
// package.json 이 "type": "module" 이라 babel-jest 의 동기 로딩을 위해 .cjs 로 둔다.
module.exports = {
  presets: [
    ['@babel/preset-env', { targets: { node: 'current' } }],
    ['@babel/preset-react', { runtime: 'automatic' }],
  ],
};
