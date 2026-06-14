import { gradeColor, gradeBg } from '../utils/formatters'

export default function GradeBadge({ grade, score, pulse = false }) {
  if (!grade) return null
  return (
    <span
      className={pulse && grade === 'A' ? 'grade-a-glow' : ''}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '5px',
        padding: '3px 9px',
        borderRadius: '20px',
        background: gradeBg(grade),
        border: `1px solid ${gradeColor(grade)}`,
        color: gradeColor(grade),
        fontSize: '12px',
        fontWeight: 700,
        fontFamily: 'JetBrains Mono, monospace',
        letterSpacing: '0.04em',
        whiteSpace: 'nowrap',
      }}
    >
      <span
        style={{
          width: 6, height: 6,
          borderRadius: '50%',
          background: gradeColor(grade),
          flexShrink: 0,
        }}
      />
      {grade}
      {score != null && (
        <span style={{ opacity: 0.7, fontSize: '11px', marginLeft: 2 }}>{Math.round(score)}</span>
      )}
    </span>
  )
}
