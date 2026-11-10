export default function BusIcon({ size = 20, ...props }) {
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
      <rect x="5" y="3" width="14" height="15" rx="2" />
      <path d="M5 7h14M5 12h14" />
      <path d="M8.5 15h.01M15.5 15h.01" />
      <path d="M8 18v2M16 18v2" />
    </svg>
  );
}
