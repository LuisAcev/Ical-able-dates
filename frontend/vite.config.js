import { defineConfig } from 'vite'
import react, { reactCompilerPreset } from '@vitejs/plugin-react'
import babel from '@rolldown/plugin-babel'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    babel({ presets: [reactCompilerPreset()] })
  ],
  server: {
    // Produccion //
    // proxy: {
    //   '/api': 'https://ical-able-dates-production.up.railway.app',
    //   '/ical': 'https://ical-able-dates-production.up.railway.app',
    // },

    // local //

        proxy: {
      '/api': 'http://localhost:8085',
      '/ical': 'http://localhost:8085',
    },
  },
})
