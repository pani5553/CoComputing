import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          100: '#E0F2FE',
          300: '#7DD3FC',
          400: '#38BDF8',
          500: '#0EA5E9',
          600: '#0284C7',
          700: '#0369A1',
        },
        success: {
          300: '#86EFAC',
          400: '#4ADE80',
          500: '#22C55E',
          600: '#16A34A',
          900: '#14532D',
        },
        danger: {
          400: '#F87171',
          500: '#EF4444',
          600: '#DC2626',
          900: '#7F1D1D',
        },
        warning: {
          400: '#FCD34D',
          500: '#F59E0B',
          600: '#D97706',
          900: '#78350F',
        },
        info: {
          400: '#60A5FA',
          500: '#3B82F6',
          600: '#2563EB',
          900: '#1E3A5F',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      animation: {
        'fade-in': 'fadeIn 0.2s ease-out',
      },
      keyframes: {
        fadeIn: {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}

export default config
