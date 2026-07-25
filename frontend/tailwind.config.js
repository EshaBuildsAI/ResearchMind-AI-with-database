/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        void: '#070f0f',
        surface: {
          DEFAULT: '#0d1a19',
          light: '#132724',
          border: '#1c3532',
        },
        teal: {
          dim: '#0f4c4c',
          DEFAULT: '#14b8a6',
          bright: '#2dd4c4',
          light: '#e6f2f1',
        },
        coral: {
          DEFAULT: '#ff6f5e',
          dark: '#e85a49',
          glow: '#ff8a7a',
        },
        ink: {
          DEFAULT: '#eaf6f4',
          muted: '#8fada8',
          faint: '#5b7975',
        },
      },
      fontFamily: {
        display: ['"Space Grotesk"', 'sans-serif'],
        body: ['"Inter"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      boxShadow: {
        glow: '0 0 24px -4px rgba(20, 184, 166, 0.35)',
        'glow-coral': '0 0 24px -4px rgba(255, 111, 94, 0.4)',
        card: '0 8px 32px -8px rgba(0, 0, 0, 0.5)',
      },
      backdropBlur: {
        xs: '2px',
      },
      keyframes: {
        pulseGlow: {
          '0%, 100%': { opacity: 0.5 },
          '50%': { opacity: 1 },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
      animation: {
        'pulse-glow': 'pulseGlow 2s ease-in-out infinite',
        shimmer: 'shimmer 2.5s linear infinite',
      },
    },
  },
  plugins: [],
}
