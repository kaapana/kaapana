<template>
  <v-card class="branding-hero">
    <v-card-text class="py-6 px-6">
      <v-row align="center">
        <v-col cols="12" md="5" class="d-flex align-center">
          <img src="@/assets/img/logo-glyph.webp" alt="Kaapana" class="brand-logo" />
          <template v-if="branding.logoUrl">
            <v-divider vertical class="mx-4" />
            <img :src="branding.logoUrl" :alt="branding.title" class="brand-logo" />
          </template>
          <div class="ml-5">
            <div class="brand-wordmark">{{ branding.title }}</div>
            <div class="brand-tagline text-medium-emphasis">
              {{ branding.text || defaultTagline }}
            </div>
          </div>
        </v-col>
        <v-col cols="12" md="7">
          <GreetingCard />
          <div class="d-flex flex-wrap mt-4">
            <v-btn
              class="mr-2 mb-1"
              variant="text"
              prepend-icon="mdi-web"
              href="https://www.kaapana.ai"
              target="_blank"
            >
              Website
            </v-btn>
            <v-btn
              class="mr-2 mb-1"
              variant="text"
              prepend-icon="mdi-slack"
              href="https://join.slack.com/t/kaapana/shared_invite/zt-hilvek0w-ucabihas~jn9PDAM0O3gVQ"
              target="_blank"
            >
              Slack
            </v-btn>
            <!-- shell route; must navigate the top window, this view runs in an iframe -->
            <v-btn
              class="mr-2 mb-1"
              variant="text"
              prepend-icon="mdi-book-open"
              href="/help"
              target="_top"
            >
              Documentation
            </v-btn>
            <v-btn
              class="mr-2 mb-1"
              variant="text"
              prepend-icon="mdi-email"
              href="mailto:kaapana@dkfz.de?subject=kaapana%20Support%20Question"
            >
              kaapana@dkfz.de
            </v-btn>
          </div>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import GreetingCard from '@/components/GreetingCard.vue'

interface Branding {
  logoUrl: string | null
  title: string
  text: string
}

const defaultTagline = 'An open-source toolkit for building medical imaging platforms.'

// Deployment-specific branding: the chart can shadow public/branding.json via
// a ConfigMap mount (see home-ui-chart values `branding:`). Absent or broken
// file means plain Kaapana defaults.
const branding = ref<Branding>({ logoUrl: null, title: 'Kaapana', text: '' })

onMounted(async () => {
  try {
    const res = await fetch(import.meta.env.BASE_URL + 'branding.json')
    if (!res.ok) return
    branding.value = { ...branding.value, ...(await res.json()) }
  } catch {
    // keep defaults
  }
})
</script>

<style scoped>
/* Echoes the kaapana.ai hero: brand-blue/cyan radial glows over a soft
   gradient, glyph + wide-tracked wordmark + tagline. */
.branding-hero {
  background:
    radial-gradient(600px 300px at 85% -20%, rgba(0, 91, 160, 0.1) 0%, rgba(0, 91, 160, 0) 60%),
    radial-gradient(500px 350px at 8% 120%, rgba(26, 180, 212, 0.14) 0%, rgba(26, 180, 212, 0) 55%),
    linear-gradient(160deg, #f2f6fa 0%, #e6eef5 55%, #dde8f1 100%);
}

.v-theme--kaapanaThemeDark .branding-hero {
  background:
    radial-gradient(600px 300px at 85% -20%, #0d3a5a 0%, rgba(13, 58, 90, 0) 60%),
    radial-gradient(500px 350px at 8% 120%, rgba(10, 84, 104, 0.6) 0%, rgba(10, 84, 104, 0) 55%),
    linear-gradient(160deg, #14212c 0%, #0e2c42 55%, #0b3a4f 100%);
}

.brand-logo {
  height: 72px;
  width: auto;
}

.brand-wordmark {
  font-size: 1.6rem;
  font-weight: 700;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: #3f5c78;
  white-space: nowrap;
}

.v-theme--kaapanaThemeDark .brand-wordmark {
  color: #dbe7f0;
}

.brand-tagline {
  max-width: 36ch;
}
</style>
