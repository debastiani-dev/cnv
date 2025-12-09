/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        './apps/**/templates/**/*.html',
        './apps/**/forms.py',
    ],
    safelist: [
        'h-8',
        'w-auto',
        'dark:text-white',
        'dark:text-gray-400',
        'dark:divide-gray-700',
        'dark:ring-white/10',
        'bg-stone-300',
        'bg-stone-400',
        'text-stone-900',
        'text-stone-600',
        'hover:bg-stone-400',
        'hover:text-stone-900',
        'bg-stone-200',
        'text-stone-700',
        'text-stone-500'
    ],
    theme: {
        extend: {},
    },
    plugins: [
        require('@tailwindcss/forms'),
        require('@tailwindcss/typography'),
        require('@tailwindcss/aspect-ratio'),
    ],
}
