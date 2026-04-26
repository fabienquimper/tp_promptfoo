import { createApp } from 'vue'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { aliases, mdi } from 'vuetify/iconsets/mdi'
import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'
import App from './App.vue'

const vuetify = createVuetify({
  components,
  directives,
  icons: { defaultSet: 'mdi', aliases, sets: { mdi } },
  theme: {
    defaultTheme: 'light',
    themes: {
      light: {
        colors: { primary: '#1565C0', secondary: '#546E7A', success: '#2E7D32', error: '#C62828' },
      },
      dark: {
        colors: { primary: '#42A5F5', secondary: '#78909C', success: '#66BB6A', error: '#EF9A9A' },
      },
    },
  },
})

createApp(App).use(vuetify).mount('#app')
