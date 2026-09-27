const CIMAS_LOGO = '/cimas-logo.png'
const HEALTHATHON_URL = 'https://innovations.cimas.co.zw/healthathon/register/'

export default function CimasLogo({ size = 'md', showLabel = true, className = '' }) {
  const heights = { sm: 'h-8', md: 'h-11', lg: 'h-14', xl: 'h-16' }

  return (
    <a
      href={HEALTHATHON_URL}
      target="_blank"
      rel="noopener noreferrer"
      className={`inline-flex flex-col items-center gap-1.5 transition opacity-90 hover:opacity-100 ${className}`}
      title="Cimas Healthathon 3.0"
    >
      <img
        src={CIMAS_LOGO}
        alt="CIMAS — Cimas Health Group"
        className={`w-auto object-contain ${heights[size] || heights.md}`}
      />
      {showLabel && (
        <span className="text-[10px] font-medium tracking-wide text-slate-400">
          Healthathon 3.0 Sponsor
        </span>
      )}
    </a>
  )
}
