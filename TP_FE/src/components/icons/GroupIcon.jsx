export default function GroupIcon({ size = 20, ...props }) {
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
      <circle cx="12" cy="7" r="2.8" />
      <path d="M7 19a5 5 0 0 1 10 0" />
      <circle cx="5" cy="9.5" r="2" />
      <path d="M2 18a3.5 3.5 0 0 1 4.5-3.4" />
      <circle cx="19" cy="9.5" r="2" />
      <path d="M22 18a3.5 3.5 0 0 0-4.5-3.4" />
    </svg>
  );
}
