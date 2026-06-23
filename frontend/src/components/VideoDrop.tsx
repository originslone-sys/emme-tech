'use client'

import { useRef } from 'react'

interface Props {
  file: File | null
  onChange: (f: File | null) => void
  videoRef?: React.RefObject<HTMLVideoElement>
  onLoaded?: (duration: number) => void
}

export default function VideoDrop({ file, onChange, videoRef, onLoaded }: Props) {
  const input = useRef<HTMLInputElement>(null)

  return (
    <div
      className="border-2 border-dashed border-white/15 rounded-xl cursor-pointer hover:border-violet-500/40 transition-colors min-h-[220px] flex flex-col items-center justify-center overflow-hidden"
      onClick={() => !file && input.current?.click()}
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => {
        e.preventDefault()
        const f = e.dataTransfer.files[0]
        if (f?.type.startsWith('video/')) onChange(f)
      }}
    >
      <input
        ref={input}
        type="file"
        accept="video/*"
        className="hidden"
        onChange={(e) => e.target.files?.[0] && onChange(e.target.files[0])}
      />
      {file ? (
        <div className="relative w-full group">
          <video
            ref={videoRef}
            src={URL.createObjectURL(file)}
            className="w-full max-h-[400px]"
            controls
            onLoadedMetadata={(e) => onLoaded?.(e.currentTarget.duration)}
          />
          <button
            className="absolute top-2 right-2 bg-red-500 hover:bg-red-600 text-white rounded-full w-7 h-7 text-sm flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity z-10"
            onClick={(e) => { e.stopPropagation(); onChange(null) }}
          >
            ×
          </button>
        </div>
      ) : (
        <>
          <div className="text-4xl text-white/15 mb-2">🎥</div>
          <p className="text-white/30 text-sm text-center px-4">Clique ou arraste o vídeo</p>
        </>
      )}
    </div>
  )
}
