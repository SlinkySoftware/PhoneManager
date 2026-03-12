/*
 * Quasar Framework configuration for @quasar/app-vite
 */
export default function () {
  return {
    framework: {
      config: {
        dark: true,
        brand: {
          primary: '#0fa36b',
          secondary: '#0b6e4f',
          accent: '#8af3c4',
          negative: '#ef5030'
        }
      },
      lang: 'en-US',
      iconSet: 'material-icons',
      plugins: []
    },
    build: {
      vueRouterMode: 'history'
    },
    devServer: {
      port: 9000,
      open: false
    }
  };
}
