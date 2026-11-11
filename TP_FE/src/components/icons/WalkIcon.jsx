export default function WalkIcon({ size = 20, ...props }) {
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
      <circle cx="13.5" cy="4.5" r="1.8" />
      <path d="M13 9l-1 6 3 2.5V21" />
      <path d="M12 15l-2.5 6" />
      <path d="M13 9l-3.5 2v3" />
      <path d="M13 9l2 3h3" />
    </svg>
  );
}
