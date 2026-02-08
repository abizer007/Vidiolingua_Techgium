'use client'

import { useState, useCallback, useEffect } from 'react'
import { useDropzone } from 'react-dropzone'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { motion } from 'framer-motion'
import { useRouter } from 'next/navigation'
import { usePipelineStore } from '@/store/pipeline-store'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { apiService } from '@/services/api'
import { Upload, Video, Languages, Volume2, User } from 'lucide-react'

const uploadSchema = z.object({
  languages: z.array(z.string()).min(1, 'Select at least one language'),
  gender: z.enum(['male', 'female', 'neutral']),
  emotion: z.enum(['neutral', 'happy', 'sad', 'excited']),
  cloned: z.boolean(),
})

type UploadFormData = z.infer<typeof uploadSchema>

const languages = [
  { code: 'hi', name: 'Hindi', flag: '🇮🇳' },
  { code: 'es', name: 'Spanish', flag: '🇪🇸' },
  { code: 'fr', name: 'French', flag: '🇫🇷' },
  { code: 'de', name: 'German', flag: '🇩🇪' },
  { code: 'ja', name: 'Japanese', flag: '🇯🇵' },
  { code: 'zh', name: 'Chinese', flag: '🇨🇳' },
  { code: 'ar', name: 'Arabic', flag: '🇸🇦' },
  { code: 'pt', name: 'Portuguese', flag: '🇵🇹' },
]

export default function UploadPage() {
  const router = useRouter()
  const { setVideoUpload, setSelectedLanguages, setVoiceOptions, startJob, isMockMode } = usePipelineStore()
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<UploadFormData>({
    resolver: zodResolver(uploadSchema),
    defaultValues: {
      languages: [],
      gender: 'neutral',
      emotion: 'neutral',
      cloned: false,
    },
  })

  const selectedLanguages = watch('languages')

  // Cleanup preview URL on unmount
  useEffect(() => {
    return () => {
      if (preview) {
        URL.revokeObjectURL(preview)
      }
    }
  }, [preview])

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const videoFile = acceptedFiles[0]
    if (videoFile) {
      // Clean up previous preview URL if it exists
      if (preview) {
        URL.revokeObjectURL(preview)
      }

      setFile(videoFile)
      const previewUrl = URL.createObjectURL(videoFile)
      setPreview(previewUrl)

      // Set video upload in store
      setVideoUpload({
        file: videoFile,
        preview: previewUrl,
        size: videoFile.size,
      })
    }
  }, [setVideoUpload, preview])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'video/*': ['.mp4', '.avi', '.mov', '.webm'],
    },
    maxFiles: 1,
  })

  const toggleLanguage = (code: string) => {
    const current = selectedLanguages || []
    const updated = current.includes(code)
      ? current.filter((l) => l !== code)
      : [...current, code]
    setValue('languages', updated)
    setSelectedLanguages(
      languages.filter((l) => updated.includes(l.code)).map((l) => ({
        code: l.code,
        name: l.name,
        flag: l.flag,
      }))
    )
  }

  const onSubmit = async (data: UploadFormData) => {
    if (!file) return

    setUploading(true)
    try {
      const { jobId } = await apiService.uploadVideo(
        file,
        data.languages,
        {
          gender: data.gender,
          emotion: data.emotion,
          cloned: data.cloned,
        }
      )

      setVoiceOptions({
        gender: data.gender,
        emotion: data.emotion,
        cloned: data.cloned,
      })

      startJob(jobId)
      router.push('/pipeline')
    } catch (error) {
      console.error('Upload failed:', error)
      alert('Upload failed. Please try again.')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="min-h-screen bg-background py-20 px-6">
      <div className="container mx-auto max-w-6xl">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h1 className="text-4xl font-bold mb-2">Upload & Configure</h1>
          <p className="text-muted-foreground">
            Upload your video and configure localization settings
          </p>
        </motion.div>

        {!isMockMode ? (
          <div className="mb-6 rounded-lg border border-green-500/50 bg-green-500/10 px-4 py-3 text-sm text-green-200">
            <strong>Real API</strong> – Backend connected. Real localized videos will be produced.
          </div>
        ) : (
          <div className="mb-6 rounded-lg border border-amber-500/50 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
            <strong>Demo mode</strong> – No real videos. Start the backend and refresh, or switch to Real API on the Architecture page.
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Video Upload */}
          <Card className="glass">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Video className="w-5 h-5" />
                Video Upload
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div
                {...getRootProps()}
                className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-all ${
                  isDragActive
                    ? 'border-primary bg-primary/10'
                    : 'border-muted-foreground/50 hover:border-primary/50'
                }`}
              >
                <input {...getInputProps()} />
                <Upload className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
                {file ? (
                  <div>
                    <p className="font-semibold">{file.name}</p>
                    <p className="text-sm text-muted-foreground mt-2">
                      {(file.size / (1024 * 1024)).toFixed(2)} MB
                    </p>
                    {preview && (
                      <video
                        src={preview}
                        controls
                        className="mt-4 max-w-full rounded-lg"
                      />
                    )}
                  </div>
                ) : (
                  <div>
                    <p className="text-lg mb-2">
                      {isDragActive
                        ? 'Drop the video here'
                        : 'Drag & drop a video file here'}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      or click to select (MP4, AVI, MOV, WebM)
                    </p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Language Selection */}
          <Card className="glass">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Languages className="w-5 h-5" />
                Target Languages
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {languages.map((lang) => (
                  <motion.button
                    key={lang.code}
                    type="button"
                    onClick={() => toggleLanguage(lang.code)}
                    className={`p-4 rounded-lg border transition-all ${
                      selectedLanguages?.includes(lang.code)
                        ? 'border-primary bg-primary/20'
                        : 'border-muted-foreground/50 hover:border-primary/50'
                    }`}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    <div className="text-2xl mb-1">{lang.flag}</div>
                    <div className="text-sm font-medium">{lang.name}</div>
                  </motion.button>
                ))}
              </div>
              {errors.languages && (
                <p className="text-destructive text-sm mt-2">
                  {errors.languages.message}
                </p>
              )}
            </CardContent>
          </Card>

          {/* Voice Options */}
          <Card className="glass">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Volume2 className="w-5 h-5" />
                Voice Options
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-sm font-medium mb-2 block">Gender</label>
                <div className="flex gap-3">
                  {(['male', 'female', 'neutral'] as const).map((gender) => (
                    <Button
                      key={gender}
                      type="button"
                      variant={watch('gender') === gender ? 'primary' : 'outline'}
                      onClick={() => setValue('gender', gender)}
                    >
                      {gender.charAt(0).toUpperCase() + gender.slice(1)}
                    </Button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-sm font-medium mb-2 block">Emotion</label>
                <div className="flex gap-3 flex-wrap">
                  {(['neutral', 'happy', 'sad', 'excited'] as const).map((emotion) => (
                    <Button
                      key={emotion}
                      type="button"
                      variant={watch('emotion') === emotion ? 'primary' : 'outline'}
                      onClick={() => setValue('emotion', emotion)}
                    >
                      {emotion.charAt(0).toUpperCase() + emotion.slice(1)}
                    </Button>
                  ))}
                </div>
              </div>

              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="cloned"
                  {...register('cloned')}
                  className="w-4 h-4"
                />
                <label htmlFor="cloned" className="text-sm">
                  Use cloned voice (requires voice sample)
                </label>
              </div>
            </CardContent>
          </Card>

          {/* Submit */}
          <div className="flex justify-end">
            <Button
              type="submit"
              size="lg"
              disabled={!file || uploading || !selectedLanguages?.length}
              className="min-w-[200px]"
            >
              {uploading ? 'Uploading...' : 'Start Processing'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
