/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        './apps/**/templates/**/*.html',
        './apps/**/forms.py',
    ],
    safelist: [
        'h-8',
        'w-auto',
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
