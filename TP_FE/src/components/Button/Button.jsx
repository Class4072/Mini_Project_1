import styles from './Button.module.css';

export default function Button({
  variant = 'primary',
  size = 'md',
  type = 'button',
  className,
  children,
  ...props
}) {
  const classNames = [styles.button, styles[variant], styles[size], className]
    .filter(Boolean)
    .join(' ');

  return (
    <button type={type} className={classNames} {...props}>
      {children}
    </button>
  );
}
