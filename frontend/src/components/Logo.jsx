const LOGO_SRC = '/safepass-logo.png'

export default function Logo({ size = 'md', className = '' }) {
  const sizes = {
    sm: 'max-h-12 w-auto',
    md: 'max-h-20 w-auto',
    lg: 'max-h-32 w-auto',
    xl: 'max-h-52 w-auto',
    sidebar: 'w-full max-w-[220px] h-auto',
  }

  return (
    <img
      src={LOGO_SRC}
      alt="SafePass — Maternal Referral & Birth Preparedness Network"
      className={`object-contain ${sizes[size] || sizes.md} ${className}`}
    />
  )
}
