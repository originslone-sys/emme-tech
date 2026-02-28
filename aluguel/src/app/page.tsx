'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import Link from 'next/link'
import {
  Home,
  Building2,
  Users,
  FileText,
  Receipt,
  Wallet,
  Shield,
  BarChart3,
  CheckCircle,
  ArrowRight,
  Star,
  Zap,
  Clock,
  TrendingUp,
  CreditCard,
  Bell,
  ChevronRight,
  Play,
  Menu,
  X,
  DollarSign,
  PieChart,
  Lock,
  Smartphone,
  Globe,
  HeartHandshake,
  MessageSquare,
  Award,
  Sparkles,
} from 'lucide-react'

// ─── Animated Counter ────────────────────────────────────────────────────────
function AnimatedCounter({ target, suffix = '', prefix = '', duration = 2000 }: {
  target: number; suffix?: string; prefix?: string; duration?: number
}) {
  const [count, setCount] = useState(0)
  const ref = useRef<HTMLSpanElement>(null)
  const started = useRef(false)

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !started.current) {
          started.current = true
          const start = Date.now()
          const step = () => {
            const elapsed = Date.now() - start
            const progress = Math.min(elapsed / duration, 1)
            const eased = 1 - Math.pow(1 - progress, 3)
            setCount(Math.floor(eased * target))
            if (progress < 1) requestAnimationFrame(step)
          }
          requestAnimationFrame(step)
        }
      },
      { threshold: 0.3 }
    )
    if (ref.current) observer.observe(ref.current)
    return () => observer.disconnect()
  }, [target, duration])

  return <span ref={ref}>{prefix}{count.toLocaleString('pt-BR')}{suffix}</span>
}

// ─── Scroll Reveal Hook ──────────────────────────────────────────────────────
function useScrollReveal() {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible')
          }
        })
      },
      { threshold: 0.1, rootMargin: '0px 0px -40px 0px' }
    )

    const el = ref.current
    if (el) {
      el.querySelectorAll('.reveal, .reveal-left, .reveal-right').forEach(child => {
        observer.observe(child)
      })
    }
    return () => observer.disconnect()
  }, [])

  return ref
}

// ─── Navbar ──────────────────────────────────────────────────────────────────
function Navbar() {
  const [scrolled, setScrolled] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20)
    window.addEventListener('scroll', onScroll)
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const navLinks = [
    { href: '#funcionalidades', label: 'Funcionalidades' },
    { href: '#como-funciona', label: 'Como Funciona' },
    { href: '#precos', label: 'Preços' },
    { href: '#depoimentos', label: 'Depoimentos' },
  ]

  return (
    <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
      scrolled ? 'glass shadow-lg shadow-black/5' : 'bg-transparent'
    }`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 lg:h-20">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2.5">
            <div className="w-9 h-9 bg-primary-600 rounded-xl flex items-center justify-center shadow-lg shadow-primary-500/20">
              <Home size={18} className="text-white" />
            </div>
            <span className="text-xl font-bold text-gray-900">AluguelPro</span>
          </Link>

          {/* Desktop Nav */}
          <div className="hidden lg:flex items-center gap-8">
            {navLinks.map(link => (
              <a key={link.href} href={link.href}
                className="text-sm font-medium text-gray-600 hover:text-primary-600 transition-colors">
                {link.label}
              </a>
            ))}
          </div>

          {/* CTA */}
          <div className="hidden lg:flex items-center gap-3">
            <Link href="/login" className="text-sm font-medium text-gray-700 hover:text-primary-600 px-4 py-2 transition-colors">
              Entrar
            </Link>
            <Link href="/registro"
              className="bg-primary-600 text-white px-5 py-2.5 rounded-xl text-sm font-semibold hover:bg-primary-700 transition-all shadow-lg shadow-primary-500/20 hover:shadow-xl hover:shadow-primary-500/30">
              Criar Conta Grátis
            </Link>
          </div>

          {/* Mobile Toggle */}
          <button className="lg:hidden p-2 text-gray-700" onClick={() => setMobileOpen(!mobileOpen)}>
            {mobileOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileOpen && (
        <div className="lg:hidden glass border-t border-gray-200/50 animate-fadeIn">
          <div className="px-4 py-4 space-y-1">
            {navLinks.map(link => (
              <a key={link.href} href={link.href} onClick={() => setMobileOpen(false)}
                className="block px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-primary-50 hover:text-primary-600 rounded-lg">
                {link.label}
              </a>
            ))}
            <div className="pt-3 border-t border-gray-200/50 space-y-2">
              <Link href="/login" className="block text-center px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg">
                Entrar
              </Link>
              <Link href="/registro" className="block text-center bg-primary-600 text-white px-4 py-2.5 rounded-lg text-sm font-semibold">
                Criar Conta Grátis
              </Link>
            </div>
          </div>
        </div>
      )}
    </nav>
  )
}

// ─── Hero Section ────────────────────────────────────────────────────────────
function HeroSection() {
  return (
    <section className="relative min-h-screen flex items-center overflow-hidden hero-grid">
      {/* Background decorations */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-[500px] h-[500px] bg-primary-400/10 rounded-full blur-3xl" />
        <div className="absolute -bottom-40 -left-40 w-[400px] h-[400px] bg-purple-400/10 rounded-full blur-3xl" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-cyan-400/5 rounded-full blur-3xl" />
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 pb-16 lg:pt-32 lg:pb-24 relative">
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
          {/* Left: Text Content */}
          <div>
            <div className="animate-float-down inline-flex items-center gap-2 bg-primary-50 border border-primary-200 text-primary-700 text-sm font-medium px-4 py-1.5 rounded-full mb-6">
              <Sparkles size={14} />
              Plataforma #1 de Gestão de Aluguéis
            </div>

            <h1 className="animate-float-up text-4xl sm:text-5xl lg:text-6xl font-extrabold text-gray-900 leading-tight tracking-tight">
              Gerencie seus
              <span className="text-gradient block">aluguéis com</span>
              inteligência
            </h1>

            <p className="animate-float-up delay-200 mt-6 text-lg sm:text-xl text-gray-600 leading-relaxed max-w-xl">
              Controle completo dos seus imóveis, inquilinos, contratos e cobranças em um único lugar.
              Receba aluguéis automaticamente e acompanhe tudo em tempo real.
            </p>

            <div className="animate-float-up delay-300 flex flex-col sm:flex-row gap-4 mt-8">
              <Link href="/registro"
                className="inline-flex items-center justify-center gap-2 bg-primary-600 text-white px-7 py-3.5 rounded-xl text-base font-semibold hover:bg-primary-700 transition-all shadow-xl shadow-primary-500/25 hover:shadow-2xl hover:shadow-primary-500/35 hover:-translate-y-0.5">
                Começar Gratuitamente
                <ArrowRight size={18} />
              </Link>
              <a href="#como-funciona"
                className="inline-flex items-center justify-center gap-2 bg-white text-gray-700 px-7 py-3.5 rounded-xl text-base font-semibold border border-gray-200 hover:bg-gray-50 hover:border-gray-300 transition-all">
                <Play size={16} className="text-primary-600" />
                Como Funciona
              </a>
            </div>

            <div className="animate-float-up delay-500 flex items-center gap-6 mt-10">
              <div className="flex -space-x-3">
                {[
                  'bg-blue-500', 'bg-green-500', 'bg-purple-500', 'bg-orange-500', 'bg-pink-500'
                ].map((color, i) => (
                  <div key={i} className={`w-9 h-9 ${color} rounded-full border-2 border-white flex items-center justify-center`}>
                    <span className="text-white text-xs font-bold">{['J','M','A','C','L'][i]}</span>
                  </div>
                ))}
              </div>
              <div>
                <div className="flex items-center gap-0.5">
                  {Array.from({ length: 5 }, (_, i) => (
                    <Star key={i} size={14} className="fill-yellow-400 text-yellow-400" />
                  ))}
                </div>
                <p className="text-sm text-gray-500 mt-0.5">
                  <strong className="text-gray-900">+2.500</strong> proprietários satisfeitos
                </p>
              </div>
            </div>
          </div>

          {/* Right: Dashboard Preview */}
          <div className="animate-scale-in delay-300 relative">
            <div className="relative">
              {/* Floating badge top-right */}
              <div className="absolute -top-4 -right-4 z-20 bg-white rounded-xl shadow-xl shadow-black/10 p-3 animate-float">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center">
                    <TrendingUp size={16} className="text-green-600" />
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Recebido</p>
                    <p className="text-sm font-bold text-green-600">+R$ 12.450</p>
                  </div>
                </div>
              </div>

              {/* Floating badge bottom-left */}
              <div className="absolute -bottom-4 -left-4 z-20 bg-white rounded-xl shadow-xl shadow-black/10 p-3 animate-float" style={{ animationDelay: '2s' }}>
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                    <Building2 size={16} className="text-blue-600" />
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Ocupação</p>
                    <p className="text-sm font-bold text-blue-600">96% dos imóveis</p>
                  </div>
                </div>
              </div>

              {/* Main Dashboard Preview */}
              <div className="bg-white rounded-2xl shadow-2xl shadow-black/10 border border-gray-200/60 overflow-hidden animate-pulse-glow">
                {/* Dashboard Header */}
                <div className="bg-slate-800 px-5 py-3 flex items-center gap-2">
                  <div className="flex gap-1.5">
                    <div className="w-3 h-3 rounded-full bg-red-400" />
                    <div className="w-3 h-3 rounded-full bg-yellow-400" />
                    <div className="w-3 h-3 rounded-full bg-green-400" />
                  </div>
                  <div className="flex-1 flex justify-center">
                    <div className="bg-slate-700/60 rounded-lg px-4 py-1 text-xs text-slate-400">
                      app.aluguelpro.com.br/dashboard
                    </div>
                  </div>
                </div>

                {/* Dashboard Content */}
                <div className="p-5">
                  {/* Stats Row */}
                  <div className="grid grid-cols-4 gap-3 mb-4">
                    {[
                      { label: 'Recebido', value: 'R$ 28.500', color: 'bg-green-500', icon: DollarSign },
                      { label: 'Em Aberto', value: 'R$ 4.200', color: 'bg-yellow-500', icon: Clock },
                      { label: 'Atrasadas', value: '2', color: 'bg-red-500', icon: Bell },
                      { label: 'Ocupação', value: '96%', color: 'bg-blue-500', icon: PieChart },
                    ].map((stat, i) => (
                      <div key={i} className="bg-gray-50 rounded-lg p-2.5">
                        <div className={`w-6 h-6 ${stat.color} rounded-md flex items-center justify-center mb-1.5`}>
                          <stat.icon size={12} className="text-white" />
                        </div>
                        <p className="text-[10px] text-gray-400 uppercase tracking-wide">{stat.label}</p>
                        <p className="text-xs font-bold text-gray-800">{stat.value}</p>
                      </div>
                    ))}
                  </div>

                  {/* Chart Placeholder */}
                  <div className="bg-gray-50 rounded-lg p-3 mb-4">
                    <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide mb-2">Receita 6 meses</p>
                    <div className="flex items-end gap-1.5 h-16">
                      {[35, 48, 42, 55, 62, 71].map((h, i) => (
                        <div key={i} className="flex-1 bg-primary-400 rounded-t-sm transition-all hover:bg-primary-500"
                          style={{ height: `${h}%` }} />
                      ))}
                    </div>
                  </div>

                  {/* Table Placeholder */}
                  <div className="space-y-1.5">
                    {['Apt 302 - Ed. Solar', 'Casa 15 - Jd. Flores', 'Sala 08 - Centro'].map((name, i) => (
                      <div key={i} className="flex items-center justify-between bg-gray-50 rounded-lg px-3 py-2">
                        <div className="flex items-center gap-2">
                          <div className="w-5 h-5 bg-primary-100 rounded flex items-center justify-center">
                            <Building2 size={10} className="text-primary-600" />
                          </div>
                          <span className="text-[11px] font-medium text-gray-700">{name}</span>
                        </div>
                        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                          i === 2 ? 'bg-yellow-100 text-yellow-700' : 'bg-green-100 text-green-700'
                        }`}>{i === 2 ? 'Pendente' : 'Pago'}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

// ─── Logos / Social Proof Bar ────────────────────────────────────────────────
function SocialProofBar() {
  return (
    <section className="relative py-12 bg-white border-y border-gray-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-8 items-center">
          {[
            { value: 2500, suffix: '+', label: 'Proprietários Ativos' },
            { value: 8700, suffix: '+', label: 'Imóveis Gerenciados' },
            { value: 15, suffix: 'M+', label: 'Em Aluguéis Processados', prefix: 'R$ ' },
            { value: 99, suffix: '%', label: 'Taxa de Satisfação' },
          ].map((stat, i) => (
            <div key={i} className="text-center">
              <p className="text-2xl sm:text-3xl font-extrabold text-gray-900">
                <AnimatedCounter target={stat.value} suffix={stat.suffix} prefix={stat.prefix} />
              </p>
              <p className="text-sm text-gray-500 mt-1">{stat.label}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

// ─── Features Section ────────────────────────────────────────────────────────
function FeaturesSection() {
  const containerRef = useScrollReveal()

  const features = [
    {
      icon: Building2,
      color: 'bg-blue-50 text-blue-600',
      title: 'Gestão de Imóveis',
      description: 'Cadastre todos os seus imóveis com detalhes completos: endereço, tipo, valor, condomínio, IPTU e status de ocupação.',
    },
    {
      icon: Users,
      color: 'bg-purple-50 text-purple-600',
      title: 'Controle de Inquilinos',
      description: 'Perfis completos dos inquilinos com dados pessoais, documentos, renda e histórico de contratos.',
    },
    {
      icon: FileText,
      color: 'bg-cyan-50 text-cyan-600',
      title: 'Contratos Inteligentes',
      description: 'Crie contratos com data de início/fim, dia de vencimento, índice de reajuste e vincule automaticamente ao imóvel.',
    },
    {
      icon: Receipt,
      color: 'bg-green-50 text-green-600',
      title: 'Cobranças Automáticas',
      description: 'Gere boletos, PIX e cobranças via cartão automaticamente. Integração completa com gateway de pagamento Asaas.',
    },
    {
      icon: Wallet,
      color: 'bg-amber-50 text-amber-600',
      title: 'Carteira Digital',
      description: 'Acompanhe seus recebimentos em tempo real. Saldo disponível para saque a qualquer momento via PIX ou TED.',
    },
    {
      icon: BarChart3,
      color: 'bg-rose-50 text-rose-600',
      title: 'Dashboard Completo',
      description: 'Visão 360° do seu patrimônio: receitas, inadimplência, ocupação, ticket médio e gráficos detalhados.',
    },
    {
      icon: Bell,
      color: 'bg-orange-50 text-orange-600',
      title: 'Alertas e Notificações',
      description: 'Receba alertas de pagamentos recebidos, cobranças atrasadas, contratos vencendo e saques processados.',
    },
    {
      icon: Shield,
      color: 'bg-indigo-50 text-indigo-600',
      title: 'Segurança Total',
      description: 'Autenticação segura com JWT, criptografia de dados, controle de permissões e logs de atividades.',
    },
    {
      icon: Smartphone,
      color: 'bg-teal-50 text-teal-600',
      title: 'Responsivo e Moderno',
      description: 'Interface adaptável a qualquer dispositivo. Gerencie seus aluguéis do computador, tablet ou celular.',
    },
  ]

  return (
    <section id="funcionalidades" className="py-20 lg:py-28 bg-gray-50" ref={containerRef}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16 reveal">
          <div className="inline-flex items-center gap-2 bg-primary-50 text-primary-700 text-sm font-medium px-4 py-1.5 rounded-full mb-4">
            <Zap size={14} /> Funcionalidades
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-gray-900 leading-tight">
            Tudo que você precisa em
            <span className="text-gradient"> um só lugar</span>
          </h2>
          <p className="text-lg text-gray-600 mt-4">
            Desenvolvido para simplificar sua vida como proprietário. Cada funcionalidade pensada para máxima eficiência.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, idx) => {
            const Icon = feature.icon
            return (
              <div key={idx} className="feature-card reveal" style={{ transitionDelay: `${idx * 60}ms` }}>
                <div className={`w-12 h-12 ${feature.color} rounded-xl flex items-center justify-center mb-4`}>
                  <Icon size={22} />
                </div>
                <h3 className="text-lg font-bold text-gray-900 mb-2">{feature.title}</h3>
                <p className="text-sm text-gray-600 leading-relaxed">{feature.description}</p>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}

// ─── How it Works ────────────────────────────────────────────────────────────
function HowItWorksSection() {
  const containerRef = useScrollReveal()

  const steps = [
    {
      number: '01',
      icon: Users,
      title: 'Crie sua Conta',
      description: 'Cadastre-se gratuitamente em menos de 1 minuto. Sem cartão de crédito, sem compromisso.',
      color: 'bg-blue-500',
    },
    {
      number: '02',
      icon: Building2,
      title: 'Cadastre seus Imóveis',
      description: 'Adicione seus imóveis, inquilinos e crie contratos de locação com todos os detalhes.',
      color: 'bg-purple-500',
    },
    {
      number: '03',
      icon: Receipt,
      title: 'Gere as Cobranças',
      description: 'Crie cobranças via boleto, PIX ou cartão. Os inquilinos recebem automaticamente.',
      color: 'bg-cyan-500',
    },
    {
      number: '04',
      icon: Wallet,
      title: 'Receba e Saque',
      description: 'Os pagamentos caem na sua carteira digital. Saque quando quiser via PIX ou transferência.',
      color: 'bg-green-500',
    },
  ]

  return (
    <section id="como-funciona" className="py-20 lg:py-28 bg-white" ref={containerRef}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16 reveal">
          <div className="inline-flex items-center gap-2 bg-green-50 text-green-700 text-sm font-medium px-4 py-1.5 rounded-full mb-4">
            <Play size={14} /> Como Funciona
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-gray-900 leading-tight">
            Simples como
            <span className="text-gradient-green"> deve ser</span>
          </h2>
          <p className="text-lg text-gray-600 mt-4">
            Em 4 passos simples você terá controle total dos seus aluguéis. Sem complicação.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
          {steps.map((step, idx) => {
            const Icon = step.icon
            return (
              <div key={idx} className="relative text-center reveal" style={{ transitionDelay: `${idx * 100}ms` }}>
                {/* Connector line */}
                {idx < steps.length - 1 && (
                  <div className="hidden lg:block absolute top-10 left-[60%] w-[80%] h-0.5">
                    <div className="w-full h-full bg-gradient-to-r from-gray-200 to-gray-100" />
                  </div>
                )}

                <div className="relative inline-flex flex-col items-center">
                  <div className={`w-20 h-20 ${step.color} rounded-2xl flex items-center justify-center mb-5 shadow-lg`}
                    style={{ boxShadow: `0 10px 30px ${step.color.replace('bg-', '').replace('-500', '')}30` }}>
                    <Icon size={32} className="text-white" />
                  </div>
                  <span className="absolute -top-2 -right-2 w-7 h-7 bg-white rounded-full border-2 border-gray-200 flex items-center justify-center text-xs font-bold text-gray-600 shadow-sm">
                    {step.number}
                  </span>
                </div>

                <h3 className="text-lg font-bold text-gray-900 mb-2">{step.title}</h3>
                <p className="text-sm text-gray-600 leading-relaxed max-w-xs mx-auto">{step.description}</p>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}

// ─── Highlight Section (Dashboard Preview) ───────────────────────────────────
function HighlightSection() {
  const containerRef = useScrollReveal()

  return (
    <section className="py-20 lg:py-28 bg-gradient-to-b from-gray-50 to-white" ref={containerRef}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
          {/* Left: Feature List */}
          <div className="reveal-left">
            <div className="inline-flex items-center gap-2 bg-purple-50 text-purple-700 text-sm font-medium px-4 py-1.5 rounded-full mb-4">
              <Award size={14} /> Por que escolher
            </div>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-gray-900 leading-tight mb-6">
              Feito para quem quer
              <span className="text-gradient"> resultado sem dor de cabeça</span>
            </h2>

            <div className="space-y-4">
              {[
                { icon: Zap, title: 'Automatize cobranças', desc: 'Pare de cobrar manualmente. O sistema gera e envia cobranças automaticamente no vencimento.' },
                { icon: TrendingUp, title: 'Acompanhe em tempo real', desc: 'Dashboard com visão completa: receitas, inadimplência, ocupação e tendências.' },
                { icon: Lock, title: 'Seus dados seguros', desc: 'Criptografia de ponta, backups automáticos e controle de acesso por perfil.' },
                { icon: CreditCard, title: 'Múltiplas formas de pagamento', desc: 'Boleto, PIX, cartão de crédito. Seu inquilino escolhe como pagar.' },
                { icon: Globe, title: 'Acesse de qualquer lugar', desc: '100% online e responsivo. Gerencie seus imóveis do celular, tablet ou computador.' },
              ].map((item, idx) => {
                const Icon = item.icon
                return (
                  <div key={idx} className="flex gap-4 p-4 rounded-xl hover:bg-gray-50 transition-colors group">
                    <div className="w-10 h-10 bg-primary-50 rounded-lg flex items-center justify-center flex-shrink-0 group-hover:bg-primary-100 transition-colors">
                      <Icon size={20} className="text-primary-600" />
                    </div>
                    <div>
                      <h4 className="text-sm font-bold text-gray-900">{item.title}</h4>
                      <p className="text-sm text-gray-500 mt-0.5">{item.desc}</p>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Right: Visual */}
          <div className="reveal-right">
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-br from-primary-400/20 to-purple-400/20 rounded-3xl transform rotate-3 scale-105" />
              <div className="relative bg-white rounded-2xl shadow-2xl shadow-black/10 p-6 border border-gray-100">
                {/* Wallet Preview */}
                <div className="bg-gradient-to-br from-primary-600 to-primary-800 rounded-xl p-5 text-white mb-5">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <p className="text-primary-200 text-xs font-medium">Saldo Disponível</p>
                      <p className="text-3xl font-bold mt-0.5">R$ 45.680,00</p>
                    </div>
                    <div className="w-10 h-10 bg-white/15 rounded-xl flex items-center justify-center">
                      <Wallet size={22} />
                    </div>
                  </div>
                  <button className="w-full bg-white/20 hover:bg-white/30 py-2 rounded-lg text-sm font-medium transition-colors">
                    Solicitar Saque
                  </button>
                </div>

                {/* Recent transactions */}
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Últimos Recebimentos</p>
                <div className="space-y-2.5">
                  {[
                    { name: 'Apt 302 - Ed. Solar', tenant: 'Maria Santos', value: 'R$ 2.100', date: 'Hoje', fee: 'R$ 20' },
                    { name: 'Casa 15 - Jd. Flores', tenant: 'Carlos Lima', value: 'R$ 1.800', date: 'Ontem', fee: 'R$ 20' },
                    { name: 'Sala 08 - Centro', tenant: 'Tech Solutions', value: 'R$ 3.500', date: '25/02', fee: 'R$ 20' },
                  ].map((item, i) => (
                    <div key={i} className="flex items-center justify-between bg-gray-50 rounded-xl px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center">
                          <ArrowRight size={14} className="text-green-600 rotate-[-135deg]" />
                        </div>
                        <div>
                          <p className="text-xs font-semibold text-gray-800">{item.name}</p>
                          <p className="text-[10px] text-gray-400">{item.tenant} - {item.date}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-xs font-bold text-green-600">+{item.value}</p>
                        <p className="text-[10px] text-gray-400">Taxa: {item.fee}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

// ─── Pricing Section ─────────────────────────────────────────────────────────
function PricingSection() {
  const containerRef = useScrollReveal()

  return (
    <section id="precos" className="py-20 lg:py-28 bg-white" ref={containerRef}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16 reveal">
          <div className="inline-flex items-center gap-2 bg-amber-50 text-amber-700 text-sm font-medium px-4 py-1.5 rounded-full mb-4">
            <CreditCard size={14} /> Preços
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-gray-900 leading-tight">
            Sem mensalidade.
            <span className="text-gradient"> Pague só quando receber.</span>
          </h2>
          <p className="text-lg text-gray-600 mt-4">
            Modelo justo e transparente. Você só paga quando seu aluguel é confirmado. Sem surpresas.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 max-w-5xl mx-auto">
          {/* Free tier */}
          <div className="pricing-card reveal" style={{ transitionDelay: '0ms' }}>
            <div className="p-8">
              <h3 className="text-lg font-bold text-gray-900">Cadastro</h3>
              <p className="text-sm text-gray-500 mt-1">Comece sem custo algum</p>
              <div className="mt-6">
                <span className="text-4xl font-extrabold text-gray-900">Grátis</span>
              </div>
              <ul className="mt-8 space-y-3">
                {[
                  'Cadastro de imóveis ilimitado',
                  'Cadastro de inquilinos',
                  'Criação de contratos',
                  'Dashboard completo',
                  'Relatórios básicos',
                ].map((item, i) => (
                  <li key={i} className="flex items-center gap-2.5 text-sm text-gray-600">
                    <CheckCircle size={16} className="text-green-500 flex-shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>
              <Link href="/registro"
                className="mt-8 block text-center bg-gray-100 text-gray-700 px-6 py-3 rounded-xl text-sm font-semibold hover:bg-gray-200 transition-colors">
                Criar Conta Grátis
              </Link>
            </div>
          </div>

          {/* Featured tier - pay per rent */}
          <div className="pricing-card-featured reveal relative" style={{ transitionDelay: '100ms' }}>
            <div className="bg-primary-600 px-8 py-2 text-center">
              <span className="text-white text-xs font-bold uppercase tracking-wider">Mais Popular</span>
            </div>
            <div className="p-8">
              <h3 className="text-lg font-bold text-gray-900">Por Recebimento</h3>
              <p className="text-sm text-gray-500 mt-1">Pague apenas quando receber</p>
              <div className="mt-6 flex items-baseline gap-1">
                <span className="text-4xl font-extrabold text-gray-900">R$ 20</span>
                <span className="text-gray-500 text-sm">/aluguel recebido</span>
              </div>
              <ul className="mt-8 space-y-3">
                {[
                  'Tudo do plano grátis',
                  'Cobranças via Boleto, PIX e Cartão',
                  'Recebimento automático',
                  'Carteira digital com saque',
                  'Notificações por e-mail',
                  'Suporte prioritário',
                  'Relatórios avançados',
                ].map((item, i) => (
                  <li key={i} className="flex items-center gap-2.5 text-sm text-gray-600">
                    <CheckCircle size={16} className="text-primary-500 flex-shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>
              <Link href="/registro"
                className="mt-8 block text-center bg-primary-600 text-white px-6 py-3 rounded-xl text-sm font-semibold hover:bg-primary-700 transition-all shadow-lg shadow-primary-500/20">
                Começar Agora
              </Link>
            </div>
          </div>

          {/* Enterprise */}
          <div className="pricing-card reveal" style={{ transitionDelay: '200ms' }}>
            <div className="p-8">
              <h3 className="text-lg font-bold text-gray-900">Imobiliária</h3>
              <p className="text-sm text-gray-500 mt-1">Para grandes carteiras</p>
              <div className="mt-6">
                <span className="text-4xl font-extrabold text-gray-900">Sob Consulta</span>
              </div>
              <ul className="mt-8 space-y-3">
                {[
                  'Tudo do plano Por Recebimento',
                  'Taxa personalizada por volume',
                  'Múltiplos usuários',
                  'API dedicada',
                  'Gerente de conta',
                  'SLA garantido',
                ].map((item, i) => (
                  <li key={i} className="flex items-center gap-2.5 text-sm text-gray-600">
                    <CheckCircle size={16} className="text-purple-500 flex-shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>
              <a href="#contato"
                className="mt-8 block text-center bg-gray-100 text-gray-700 px-6 py-3 rounded-xl text-sm font-semibold hover:bg-gray-200 transition-colors">
                Falar com Consultor
              </a>
            </div>
          </div>
        </div>

        {/* Fee explanation */}
        <div className="max-w-3xl mx-auto mt-12 reveal">
          <div className="bg-gradient-to-r from-primary-50 to-blue-50 rounded-2xl p-6 sm:p-8 border border-primary-100">
            <div className="flex flex-col sm:flex-row items-start gap-4">
              <div className="w-12 h-12 bg-primary-100 rounded-xl flex items-center justify-center flex-shrink-0">
                <HeartHandshake size={24} className="text-primary-600" />
              </div>
              <div>
                <h4 className="text-lg font-bold text-gray-900">Modelo justo para todos</h4>
                <p className="text-sm text-gray-600 mt-1 leading-relaxed">
                  Cobramos apenas <strong>R$ 20,00 por aluguel recebido</strong>. Se você não receber, não paga nada.
                  O valor é descontado automaticamente e o líquido fica disponível na sua carteira para saque
                  quando quiser. Sem taxa de adesão, sem mensalidade, sem fidelidade.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

// ─── Testimonials ────────────────────────────────────────────────────────────
function TestimonialsSection() {
  const containerRef = useScrollReveal()

  const testimonials = [
    {
      name: 'Roberto Mendes',
      role: 'Proprietário - 12 imóveis',
      avatar: 'RM',
      color: 'bg-blue-500',
      text: 'Gerenciava meus aluguéis por planilha e vivia esquecendo cobranças. Com o AluguelPro automatizei tudo. Hoje recebo tudo em dia e acompanho pelo celular.',
      rating: 5,
    },
    {
      name: 'Ana Carolina Silva',
      role: 'Proprietária - 5 imóveis',
      avatar: 'AC',
      color: 'bg-purple-500',
      text: 'A taxa de R$20 por recebimento é muito justa. Antes pagava R$200/mês numa plataforma e usava 10% das funcionalidades. Aqui pago só quando recebo.',
      rating: 5,
    },
    {
      name: 'Marcos Paulo',
      role: 'Investidor Imobiliário',
      avatar: 'MP',
      color: 'bg-green-500',
      text: 'O dashboard é incrível. Consigo ver a saúde financeira de toda minha carteira em segundos. Taxa de ocupação, inadimplência, ticket médio... tudo na tela.',
      rating: 5,
    },
    {
      name: 'Fernanda Costa',
      role: 'Proprietária - 8 imóveis',
      avatar: 'FC',
      color: 'bg-rose-500',
      text: 'Meus inquilinos adoram pagar por PIX e recebem o QR Code automaticamente. A inadimplência caiu drasticamente desde que comecei a usar o sistema.',
      rating: 5,
    },
    {
      name: 'Eduardo Campos',
      role: 'Imobiliária - 45 imóveis',
      avatar: 'EC',
      color: 'bg-amber-500',
      text: 'Migrei minha imobiliária inteira pro AluguelPro. O painel admin me dá controle total dos clientes. Economizei horas por semana em trabalho operacional.',
      rating: 5,
    },
    {
      name: 'Luciana Rodrigues',
      role: 'Proprietária - 3 imóveis',
      avatar: 'LR',
      color: 'bg-cyan-500',
      text: 'Comecei com 1 imóvel e hoje tenho 3. O sistema cresce junto comigo. A carteira digital é maravilhosa - saco meus rendimentos toda semana por PIX.',
      rating: 5,
    },
  ]

  return (
    <section id="depoimentos" className="py-20 lg:py-28 bg-gray-50" ref={containerRef}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16 reveal">
          <div className="inline-flex items-center gap-2 bg-rose-50 text-rose-700 text-sm font-medium px-4 py-1.5 rounded-full mb-4">
            <MessageSquare size={14} /> Depoimentos
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-gray-900 leading-tight">
            Quem usa,
            <span className="text-gradient"> recomenda</span>
          </h2>
          <p className="text-lg text-gray-600 mt-4">
            Milhares de proprietários já transformaram a gestão dos seus aluguéis.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {testimonials.map((t, idx) => (
            <div key={idx} className="testimonial-card reveal" style={{ transitionDelay: `${idx * 80}ms` }}>
              <div className="flex items-center gap-0.5 mb-4">
                {Array.from({ length: t.rating }, (_, i) => (
                  <Star key={i} size={14} className="fill-yellow-400 text-yellow-400" />
                ))}
              </div>
              <p className="text-sm text-gray-600 leading-relaxed mb-5">&ldquo;{t.text}&rdquo;</p>
              <div className="flex items-center gap-3 pt-4 border-t border-gray-100">
                <div className={`w-10 h-10 ${t.color} rounded-full flex items-center justify-center`}>
                  <span className="text-white text-xs font-bold">{t.avatar}</span>
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-900">{t.name}</p>
                  <p className="text-xs text-gray-500">{t.role}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

// ─── CTA Section ─────────────────────────────────────────────────────────────
function CTASection() {
  const containerRef = useScrollReveal()

  return (
    <section className="py-20 lg:py-28 bg-white" ref={containerRef}>
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center reveal">
        <div className="relative bg-gradient-to-br from-primary-600 via-primary-700 to-blue-800 rounded-3xl p-10 sm:p-16 overflow-hidden">
          {/* Decorations */}
          <div className="absolute inset-0 overflow-hidden pointer-events-none">
            <div className="absolute -top-20 -right-20 w-60 h-60 bg-white/5 rounded-full" />
            <div className="absolute -bottom-20 -left-20 w-48 h-48 bg-white/5 rounded-full" />
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-white/3 rounded-full" />
          </div>

          <div className="relative">
            <div className="inline-flex items-center gap-2 bg-white/15 text-white text-sm font-medium px-4 py-1.5 rounded-full mb-6">
              <Sparkles size={14} /> Comece agora mesmo
            </div>
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-white leading-tight">
              Pronto para transformar a
              <br />
              gestão dos seus aluguéis?
            </h2>
            <p className="text-lg text-primary-100 mt-4 max-w-2xl mx-auto">
              Junte-se a mais de 2.500 proprietários que já economizam tempo e dinheiro com o AluguelPro.
              Comece gratuitamente, sem compromisso.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mt-8">
              <Link href="/registro"
                className="inline-flex items-center gap-2 bg-white text-primary-700 px-8 py-4 rounded-xl text-base font-bold hover:bg-gray-50 transition-all shadow-xl shadow-black/10 hover:shadow-2xl">
                Criar Minha Conta Grátis
                <ArrowRight size={18} />
              </Link>
              <Link href="/login"
                className="inline-flex items-center gap-2 text-white/90 text-sm font-medium hover:text-white transition-colors">
                Já tenho conta
                <ChevronRight size={16} />
              </Link>
            </div>
            <p className="text-primary-200 text-sm mt-6">
              Sem cartão de crédito. Sem mensalidade. Configure em 2 minutos.
            </p>
          </div>
        </div>
      </div>
    </section>
  )
}

// ─── FAQ Section ─────────────────────────────────────────────────────────────
function FAQSection() {
  const containerRef = useScrollReveal()
  const [openIndex, setOpenIndex] = useState<number | null>(null)

  const faqs = [
    {
      q: 'Quanto custa usar o AluguelPro?',
      a: 'O cadastro e uso da plataforma é gratuito. Cobramos apenas R$ 20,00 por aluguel recebido pelo sistema. Se você não receber nenhum aluguel, não paga nada. Sem mensalidade, sem taxa de adesão.',
    },
    {
      q: 'Como funciona o recebimento dos aluguéis?',
      a: 'Você cria a cobrança no sistema e o inquilino recebe automaticamente o boleto, PIX ou link para pagamento com cartão. Quando o pagamento é confirmado, o valor líquido (aluguel - R$20 de taxa) é creditado na sua carteira digital.',
    },
    {
      q: 'Quando posso sacar meu saldo?',
      a: 'A qualquer momento! Seu saldo fica disponível na carteira digital e você pode solicitar saque via PIX (instantâneo) ou transferência bancária quando quiser. Não há valor mínimo para saque.',
    },
    {
      q: 'Quantos imóveis posso cadastrar?',
      a: 'Não há limite. Você pode cadastrar quantos imóveis, inquilinos e contratos precisar. A plataforma cresce com você.',
    },
    {
      q: 'O sistema é seguro?',
      a: 'Sim. Usamos criptografia de ponta a ponta, autenticação JWT segura, e os pagamentos são processados pela Asaas, gateway de pagamento certificado pelo Banco Central. Seus dados e de seus inquilinos estão protegidos.',
    },
    {
      q: 'Preciso instalar algum aplicativo?',
      a: 'Não. O AluguelPro é 100% online e funciona direto no navegador do seu computador, tablet ou celular. Sem downloads, sem instalação.',
    },
  ]

  return (
    <section className="py-20 lg:py-28 bg-gray-50" ref={containerRef}>
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12 reveal">
          <h2 className="text-3xl sm:text-4xl font-extrabold text-gray-900">
            Perguntas Frequentes
          </h2>
          <p className="text-gray-600 mt-3">Tudo que você precisa saber antes de começar</p>
        </div>

        <div className="space-y-3 reveal" style={{ transitionDelay: '100ms' }}>
          {faqs.map((faq, idx) => (
            <div key={idx} className="bg-white rounded-xl border border-gray-100 overflow-hidden transition-all duration-200 hover:border-gray-200">
              <button
                onClick={() => setOpenIndex(openIndex === idx ? null : idx)}
                className="w-full flex items-center justify-between px-6 py-4 text-left"
              >
                <span className="text-sm font-semibold text-gray-900 pr-4">{faq.q}</span>
                <ChevronRight
                  size={18}
                  className={`text-gray-400 flex-shrink-0 transition-transform duration-200 ${openIndex === idx ? 'rotate-90' : ''}`}
                />
              </button>
              {openIndex === idx && (
                <div className="px-6 pb-4 animate-fadeIn">
                  <p className="text-sm text-gray-600 leading-relaxed">{faq.a}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

// ─── Footer ──────────────────────────────────────────────────────────────────
function Footer() {
  return (
    <footer className="bg-slate-900 text-gray-400" id="contato">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-10">
          {/* Brand */}
          <div className="lg:col-span-1">
            <div className="flex items-center gap-2.5 mb-4">
              <div className="w-9 h-9 bg-primary-600 rounded-xl flex items-center justify-center">
                <Home size={18} className="text-white" />
              </div>
              <span className="text-xl font-bold text-white">AluguelPro</span>
            </div>
            <p className="text-sm leading-relaxed mb-5">
              Plataforma profissional de gestão de aluguéis para proprietários de imóveis.
              Simples, seguro e eficiente.
            </p>
            <div className="flex items-center gap-1">
              {Array.from({ length: 5 }, (_, i) => (
                <Star key={i} size={14} className="fill-yellow-400 text-yellow-400" />
              ))}
              <span className="text-xs text-gray-500 ml-1">4.9/5 (2.500+ avaliações)</span>
            </div>
          </div>

          {/* Product */}
          <div>
            <h4 className="text-white text-sm font-semibold mb-4">Produto</h4>
            <ul className="space-y-2.5">
              {['Funcionalidades', 'Preços', 'Como Funciona', 'Integrações', 'API'].map((item, i) => (
                <li key={i}>
                  <a href="#" className="text-sm hover:text-white transition-colors">{item}</a>
                </li>
              ))}
            </ul>
          </div>

          {/* Company */}
          <div>
            <h4 className="text-white text-sm font-semibold mb-4">Empresa</h4>
            <ul className="space-y-2.5">
              {['Sobre Nós', 'Blog', 'Carreiras', 'Parceiros', 'Contato'].map((item, i) => (
                <li key={i}>
                  <a href="#" className="text-sm hover:text-white transition-colors">{item}</a>
                </li>
              ))}
            </ul>
          </div>

          {/* Legal */}
          <div>
            <h4 className="text-white text-sm font-semibold mb-4">Legal</h4>
            <ul className="space-y-2.5">
              {['Termos de Uso', 'Privacidade', 'LGPD', 'Segurança', 'SLA'].map((item, i) => (
                <li key={i}>
                  <a href="#" className="text-sm hover:text-white transition-colors">{item}</a>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="mt-12 pt-8 border-t border-gray-800 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-xs text-gray-500">
            &copy; {new Date().getFullYear()} AluguelPro. Todos os direitos reservados.
          </p>
          <div className="flex items-center gap-4">
            <span className="text-xs text-gray-600">Pagamentos seguros via</span>
            <div className="flex items-center gap-2">
              <div className="bg-gray-800 rounded px-2.5 py-1 text-[10px] font-bold text-gray-400">ASAAS</div>
              <div className="bg-gray-800 rounded px-2.5 py-1 text-[10px] font-bold text-gray-400">PIX</div>
              <div className="bg-gray-800 rounded px-2.5 py-1 text-[10px] font-bold text-gray-400">BOLETO</div>
            </div>
          </div>
        </div>
      </div>
    </footer>
  )
}

// ─── Main Page ───────────────────────────────────────────────────────────────
export default function HomePage() {
  return (
    <main className="bg-white">
      <Navbar />
      <HeroSection />
      <SocialProofBar />
      <FeaturesSection />
      <HowItWorksSection />
      <HighlightSection />
      <PricingSection />
      <TestimonialsSection />
      <CTASection />
      <FAQSection />
      <Footer />
    </main>
  )
}
