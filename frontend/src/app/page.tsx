import Link from 'next/link'

const cards = [
  {
    href: '/cortes',
    icon: '🔥',
    title: 'Cortes Virais',
    description: 'Transforme um vídeo longo (upload ou link do YouTube) em cortes verticais com legenda, prontos pra TikTok, Reels e Shorts — com título, descrição e tags gerados por IA.',
  },
  {
    href: '/editar',
    icon: '🎬',
    title: 'Editar Vídeo',
    description: 'Corte, ajuste a iluminação e melhore a qualidade — tudo de uma vez e exporte num clique.',
  },
  {
    href: '/juntar',
    icon: '🎞️',
    title: 'Juntar Vídeos',
    description: 'Monte uma linha do tempo unindo vários vídeos em sequência.',
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
