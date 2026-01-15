/*
 * Quasar Framework configuration
 */
import { configure } from 'quasar/wrappers';

export default configure(() => ({
  supportTS: false,
  cssAddon: true,
  extras: ['material-icons'],
  build: {
    target: {
      browser: ['es2022', 'edge105', 'firefox104', 'chrome110', 'safari16'],
      node: 'node20'
    },
    env: {
      VITE_API_BASE: process.env.VITE_API_BASE || 'http://localhost:8000/api'
    }
  },
  devServer: {
    https: false,
    port: 9000,
    open: false
  },
  framework: {
    config: {
      dark: true,
      brand: {
        primary: '#0fa36b',
        secondary: '#0b6e4f',
        accent: '#8af3c4'
      }
    },
    plugins: []
  },
  animations: []
}));
