export default function ElderIcon({ size = 20, ...props }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      <circle cx="10" cy="5" r="2.5" />
      <path d="M10 8.5v6l-3 5.5" />
      <path d="M10 14.5l2.5 5.5" />
      <path d="M10 10.5l4.5 1.5" />
      <path d="M14.5 9.5a1.75 1.75 0 0 1 3.5 0V20" />
    </svg>
  );
}
