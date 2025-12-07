/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        './apps/**/templates/**/*.html',
        './apps/**/forms.py',
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
