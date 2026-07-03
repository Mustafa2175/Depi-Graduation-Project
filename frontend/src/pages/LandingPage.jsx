import '../landing.css';
import { motion } from 'motion/react';
import { BarChart2, TrendingUp, MapPin, Briefcase } from 'lucide-react';
import { Link } from 'react-router-dom';

/* ─── Tech Logo data (all sourced from simpleicons CDN for reliability) ─── */
const TECH_LOGOS = [
  {
    alt: 'Python',
    src: 'https://cdn.simpleicons.org/python/3776AB',
    gradient: { from: '#3776AB', to: '#FFD43B' },
  },
  {
    alt: 'React',
    src: 'https://cdn.simpleicons.org/react/61DAFB',
    gradient: { from: '#61DAFB', to: '#0D6EFD' },
  },
  {
    alt: 'AWS',
    src: 'https://cdn.simpleicons.org/amazonaws/FF9900',
    gradient: { from: '#FF9900', to: '#232F3E' },
  },
  {
    alt: 'Docker',
    src: 'https://cdn.simpleicons.org/docker/2496ED',
    gradient: { from: '#2496ED', to: '#003f8a' },
  },
  {
    alt: 'PostgreSQL',
    src: 'https://cdn.simpleicons.org/postgresql/4169E1',
    gradient: { from: '#4169E1', to: '#336791' },
  },
  {
    alt: 'Apache Airflow',
    src: 'https://cdn.simpleicons.org/apacheairflow/017CEE',
    gradient: { from: '#017CEE', to: '#00427E' },
  },
  {
    alt: 'dbt',
    src: 'https://cdn.simpleicons.org/dbt/FF694B',
    gradient: { from: '#FF694B', to: '#C93A1E' },
  },
  {
    alt: 'Kubernetes',
    src: 'https://cdn.simpleicons.org/kubernetes/326CE5',
    gradient: { from: '#326CE5', to: '#003087' },
  },
  {
    alt: 'TypeScript',
    src: 'https://cdn.simpleicons.org/typescript/3178C6',
    gradient: { from: '#3178C6', to: '#235A97' },
  },
  {
    alt: 'Selenium',
    src: 'https://cdn.simpleicons.org/selenium/43B02A',
    gradient: { from: '#43B02A', to: '#1B5E20' },
  },
  {
    alt: 'Vite',
    src: 'https://cdn.simpleicons.org/vite/646CFF',
    gradient: { from: '#646CFF', to: '#BD34FE' },
  },
  {
    alt: 'FastAPI',
    src: 'https://cdn.simpleicons.org/fastapi/009688',
    gradient: { from: '#009688', to: '#00695C' },
  },
];

/* ─── Stat Pills ─────────────────────────────────────────── */
const STATS = [
  { icon: <Briefcase size={14} />, label: '190+ Job Postings Tracked' },
  { icon: <MapPin size={14} />, label: '5 Egyptian Job Boards Scraped' },
  { icon: <TrendingUp size={14} />, label: 'Real-Time Salary Intelligence' },
  { icon: <BarChart2 size={14} />, label: 'Skills & Demand Analytics' },
];

/* ─── Marquee Scroller ───────────────────────────────────── */
function MarqueeScroller() {
  const doubled = [...TECH_LOGOS, ...TECH_LOGOS];

  return (
    <div
      className="relative w-full overflow-hidden"
      style={{
        maskImage:
          'linear-gradient(to right, transparent 0%, black 8%, black 92%, transparent 100%)',
        WebkitMaskImage:
          'linear-gradient(to right, transparent 0%, black 8%, black 92%, transparent 100%)',
      }}
    >
      <div className="marquee-track flex gap-4 w-max py-2">
        {doubled.map((logo, idx) => (
          <div
            key={`${logo.alt}-${idx}`}
            className="group relative h-24 w-44 shrink-0 flex flex-col items-center justify-center rounded-2xl bg-[#111] border border-white/10 shadow-lg hover:border-white/30 transition-all overflow-hidden cursor-pointer gap-2"
          >
            {/* Hover gradient glow */}
            <div
              className="absolute inset-0 opacity-0 group-hover:opacity-15 transition-all duration-500 rounded-2xl"
              style={{
                background: `radial-gradient(ellipse at center, ${logo.gradient.from}, ${logo.gradient.to})`,
              }}
            />
            <img
              src={logo.src}
              alt={logo.alt}
              className="relative z-10 h-9 w-9 object-contain transition-all duration-300 group-hover:scale-110"
              loading="lazy"
              onError={(e) => {
                e.currentTarget.style.display = 'none';
              }}
            />
            <span className="relative z-10 text-[10px] font-semibold text-white/30 group-hover:text-white/70 transition-colors tracking-wider uppercase">
              {logo.alt}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ─── Main Landing Page ──────────────────────────────────── */
export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#060608] flex flex-col font-sans">

      {/* ── Hero Container — full-width, no max-width clipping ── */}
      <div className="relative w-full flex-1 bg-[#0a0a0f] overflow-hidden" style={{ minHeight: '92vh' }}>

        {/* Background Video */}
        <div className="absolute inset-0 pointer-events-none z-0 overflow-hidden select-none">
          <video
            src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260505_101331_74f9b798-3f00-4e86-8a01-377aa16ffeaa.mp4"
            autoPlay
            loop
            muted
            playsInline
            className="w-full h-full object-cover opacity-30"
          />
          {/* Gradient overlays for text readability */}
          <div className="absolute inset-0 bg-gradient-to-br from-[#0a0a0f]/80 via-[#0a0a0f]/50 to-transparent" />
          <div className="absolute inset-0 bg-gradient-to-b from-[#0a0a0f]/40 via-transparent to-[#060608]" />
        </div>

        {/* ── Top Bar ── */}
        <div className="relative z-20 flex items-center justify-between px-8 md:px-16 pt-8">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold text-sm">
              📡
            </div>
            <div>
              <span className="text-white font-bold text-sm tracking-wide">Egyptian Job Market</span>
              <span className="ml-1 text-white/40 font-semibold text-sm">Tracker</span>
            </div>
          </div>

          {/* Live indicator */}
          <div className="flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/20 rounded-full px-4 py-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-emerald-400 text-[11px] font-semibold tracking-widest uppercase">Live Data</span>
          </div>
        </div>

        {/* ── Hero Text Content — centred vertically ── */}
        <div className="relative z-20 flex flex-col items-center justify-center text-center px-6 md:px-20"
          style={{ minHeight: 'calc(92vh - 100px)' }}
        >
          <motion.div
            initial={{ opacity: 0, y: 32 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
            className="flex flex-col items-center gap-7 max-w-4xl"
          >
            {/* Eyebrow badge */}
            <div className="flex items-center gap-2 bg-white/[0.06] border border-white/[0.10] rounded-full px-5 py-2 text-[12px] font-semibold text-white/50 tracking-widest uppercase">
              <span className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
              Egyptian Job Market Tracker — DEPI Graduation Project
            </div>

            {/* Headline */}
            <h1 className="font-display text-[48px] md:text-[70px] font-bold leading-[1.06] tracking-tight text-white">
              Egypt's Tech Job Market,{' '}
              <br />
              <span className="bg-gradient-to-r from-indigo-400 via-violet-400 to-cyan-400 bg-clip-text text-transparent">
                Decoded in Real-Time
              </span>
            </h1>

            {/* Subheadline */}
            <p className="font-sans text-[16px] md:text-[18px] text-white/50 leading-relaxed max-w-2xl">
              Scraping 190+ job postings daily from Wuzzuf, Forasna, Bayt, Jobzella and Indeed —
              then transforming them into salary intelligence, skill rankings, and hiring trends
              for Egypt's tech landscape.
            </p>

            {/* Single CTA button */}
            <Link to="/dashboard">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.97 }}
                transition={{ type: 'spring', stiffness: 400, damping: 18 }}
                className="mt-2 bg-gradient-to-r from-indigo-500 to-violet-600 text-white font-bold text-[15px] px-10 py-4 rounded-full shadow-[0_0_40px_rgba(99,102,241,0.35)] hover:shadow-[0_0_60px_rgba(99,102,241,0.55)] transition-shadow cursor-pointer border-0"
              >
                Explore the Dashboard →
              </motion.button>
            </Link>

            {/* Stat pills row */}
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.4, ease: [0.22, 1, 0.36, 1] }}
              className="flex flex-wrap items-center justify-center gap-3 mt-2"
            >
              {STATS.map((s) => (
                <div
                  key={s.label}
                  className="flex items-center gap-2 bg-white/[0.05] border border-white/[0.08] rounded-full px-4 py-2 text-[12px] text-white/50 font-medium"
                >
                  <span className="text-indigo-400">{s.icon}</span>
                  {s.label}
                </div>
              ))}
            </motion.div>
          </motion.div>
        </div>
      </div>

      {/* ── Marquee Logo Scroller ── */}
      <div className="w-full bg-[#060608] py-8 border-t border-white/[0.04]">
        <p className="text-center text-[11px] font-semibold text-white/20 tracking-widest uppercase mb-6">
          Powered by the modern data stack
        </p>
        <MarqueeScroller />
      </div>
    </div>
  );
}
