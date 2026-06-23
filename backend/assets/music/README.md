# Biblioteca de músicas (livres de direitos)

Coloque trilhas livres de direitos autorais aqui, organizadas por clima/mood.
A IA escolhe um mood para cada vídeo e o backend sorteia uma faixa da pasta
correspondente. Se a pasta estiver vazia, o vídeo é gerado sem trilha (o
usuário também pode enviar a própria música na tela de geração).

```
music/
  energetic/    *.mp3
  upbeat/       *.mp3
  inspirational/*.mp3
  calm/         *.mp3
  dramatic/     *.mp3
  epic/         *.mp3
```

Formatos aceitos: `.mp3 .m4a .aac .wav .ogg`.

Pode apontar para outro diretório (ex: um volume montado no Railway) com a
variável de ambiente `MUSIC_DIR`.

> Importante: este caminho local só é usado no **render local**. No render via
> worker RunPod, a música precisa ser uma URL pública — use o upload de música
> na tela de geração (servido pelo backend em `/files/uploads/...`).

Boas fontes de música livre: Pixabay Music, YouTube Audio Library, Free Music
Archive (verifique sempre a licença de cada faixa).
