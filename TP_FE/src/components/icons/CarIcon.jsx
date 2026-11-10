export default function CarIcon({ size = 20, ...props }) {
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
      <path d="M5 11l1.6-4.2A1.5 1.5 0 0 1 8 5.8h8a1.5 1.5 0 0 1 1.4 1L19 11" />
      <rect x="3" y="11" width="18" height="6" rx="1.5" />
      <path d="M6 17v2M18 17v2" />
      <path d="M7 14h.01M17 14h.01" />
    </svg>
  );
}
