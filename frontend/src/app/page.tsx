import Link from 'next/link'

const cards = [
  {
    href: '/melhorar',
    icon: '✨',
    title: 'Melhorar Qualidade',
    description: 'Aumente a resolução, nitidez e reduza ruído de vídeos de baixa qualidade com IA.',
  },
  {
    href: '/cortar',
    icon: '✂️',
    title: 'Cortar',
    description: 'Remova as partes que você não quer, escolhendo o início e o fim do trecho.',
  },
  {
    href: '/juntar',
    icon: '🎞️',
    title: 'Juntar Vídeos',
    description: 'Monte uma linha do tempo unindo vários vídeos em sequência.',
  },
  {
    href: '/ajustar',
    icon: '💡',
    title: 'Iluminação',
    description: 'Ajuste brilho, contraste e saturação para melhorar a aparência do vídeo.',
  },
  {
    href: '/biblioteca',
    icon: '📁',
    title: 'Biblioteca',
    description: 'Acesse todos os vídeos processados. Baixe ou exclua quando quiser.',
  },
]

export default function Home() {
  return (
    <div className="max-w-3xl mx-auto">
      <div className="mb-10">
        <h1 className="text-3xl font-bold text-white">Editor de Vídeo</h1>
        <p className="text-white/40 mt-1">Melhore, corte e monte seus vídeos</p>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {cards.map((card) => (
          <Link
            key={card.href}
            href={card.href}
            className="group flex items-start gap-5 p-6 bg-[#111] border border-white/10 rounded-xl hover:border-violet-500/40 transition-all"
          >
            <div className="text-3xl mt-0.5">{card.icon}</div>
            <div className="flex-1">
              <h2 className="text-base font-semibold text-white">{card.title}</h2>
              <p className="text-sm text-white/40 mt-1">{card.description}</p>
            </div>
            <span className="text-violet-400 group-hover:text-violet-300 text-sm self-center transition-colors">
              →
            </span>
          </Link>
        ))}
      </div>
    </div>
  )
}
