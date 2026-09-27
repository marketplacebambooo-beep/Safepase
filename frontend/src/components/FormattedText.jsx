function renderInline(text) {
  if (!text) return null
  const parts = text.split(/(\*\*[^*]+\*\*)/g)
  return parts.map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={index} className="font-semibold text-slate-900">{part.slice(2, -2)}</strong>
    }
    return part
  })
}

function parseBlocks(text) {
  if (!text?.trim()) return []

  const blocks = []
  const lines = text.replace(/\r\n/g, '\n').split('\n')
  let index = 0

  while (index < lines.length) {
    const line = lines[index].trim()
    if (!line) {
      index += 1
      continue
    }

    if (line.startsWith('## ')) {
      blocks.push({ type: 'h2', content: line.slice(3).trim() })
      index += 1
      continue
    }

    if (line.startsWith('### ')) {
      blocks.push({ type: 'h3', content: line.slice(4).trim() })
      index += 1
      continue
    }

    if (/^[-*]\s/.test(line)) {
      const items = []
      while (index < lines.length && /^[-*]\s/.test(lines[index].trim())) {
        items.push(lines[index].trim().replace(/^[-*]\s/, ''))
        index += 1
      }
      blocks.push({ type: 'ul', items })
      continue
    }

    const paragraph = [line]
    index += 1
    while (
      index < lines.length
      && lines[index].trim()
      && !lines[index].trim().startsWith('#')
      && !/^[-*]\s/.test(lines[index].trim())
    ) {
      paragraph.push(lines[index].trim())
      index += 1
    }

    const content = paragraph.join(' ')
    if (/^\*\*[^*]+\*\*$/.test(content)) {
      blocks.push({ type: 'h3', content: content.slice(2, -2) })
    } else {
      blocks.push({ type: 'p', content })
    }
  }

  return blocks
}

export default function FormattedText({ text, className = '' }) {
  const blocks = parseBlocks(text)

  if (!blocks.length) return null

  return (
    <div className={`space-y-4 ${className}`}>
      {blocks.map((block, index) => {
        if (block.type === 'h2') {
          return (
            <h2 key={index} className="text-lg font-bold text-slate-900 md:text-xl">
              {renderInline(block.content)}
            </h2>
          )
        }
        if (block.type === 'h3') {
          return (
            <h3 key={index} className="text-base font-semibold text-slate-800">
              {renderInline(block.content)}
            </h3>
          )
        }
        if (block.type === 'ul') {
          return (
            <ul key={index} className="list-disc space-y-2 pl-5 text-slate-700">
              {block.items.map((item) => (
                <li key={item} className="leading-relaxed">{renderInline(item)}</li>
              ))}
            </ul>
          )
        }
        return (
          <p key={index} className="text-base leading-relaxed text-slate-700 md:text-lg">
            {renderInline(block.content)}
          </p>
        )
      })}
    </div>
  )
}
