import type { ButtonHTMLAttributes, ReactNode } from 'react'

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'
type ButtonSize = 'sm' | 'md' | 'lg'

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant
  size?: ButtonSize
  loading?: boolean
  leftIcon?: ReactNode
  rightIcon?: ReactNode
}

const classNames = (...values: Array<string | false | null | undefined>) => values.filter(Boolean).join(' ')

export const Button = ({
  children,
  className,
  disabled,
  leftIcon,
  loading = false,
  rightIcon,
  size = 'md',
  type = 'button',
  variant = 'primary',
  ...props
}: ButtonProps) => {
  const isDisabled = disabled || loading

  return (
    <button
      className={classNames('cg-button', `cg-button--${variant}`, `cg-button--${size}`, className)}
      type={type}
      disabled={isDisabled}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading ? <span className="cg-button__spinner" aria-hidden="true" /> : leftIcon}
      <span>{children}</span>
      {loading ? <span className="cg-visually-hidden">Загрузка</span> : rightIcon}
    </button>
  )
}
