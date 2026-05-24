'use client'

import { useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import {
  Upload,
  FileText,
  Settings2,
  Send,
  Check,
  ArrowLeft,
  ArrowRight,
  Sparkles,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Eye,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { createTask, type CreateTaskPayload, uploadFile } from '@/lib/api'
import FileUpload from '@/components/Upload/FileUpload'
import ConfigPanel from '@/components/ConfigPanel/ConfigPanel'
import type { ConfigValues } from '@/components/ConfigPanel/ConfigPanel'

const steps = [
  { id: 1, title: 'Upload Images', description: 'Drag & drop product images', icon: Upload },
  { id: 2, title: 'Description', description: 'Describe your product', icon: FileText },
  { id: 3, title: 'Configure', description: 'Set video parameters', icon: Settings2 },
  { id: 4, title: 'Review & Submit', description: 'Finalize and generate', icon: Send },
]

interface ProgressState {
  show: boolean
  status: 'preparing' | 'uploading' | 'generating' | 'done' | 'error'
  message: string
  percent: number
}

export default function CreatePage() {
  const router = useRouter()
  const [currentStep, setCurrentStep] = useState(1)
  const [imageUrls, setImageUrls] = useState<string[]>([])
  const [description, setDescription] = useState('')
  const [config, setConfig] = useState<ConfigValues>({
    platform: 'tiktok',
    style: 'apple',
    language: 'en',
    videoLength: 30,
    model: 'standard',
  })
  const [submitting, setSubmitting] = useState(false)
  const [progress, setProgress] = useState<ProgressState>({
    show: false,
    status: 'preparing',
    message: '',
    percent: 0,
  })

  const totalSteps = steps.length

  const handleImagesReady = useCallback((urls: string[]) => {
    setImageUrls(urls)
  }, [])

  const canProceedStep1 = imageUrls.length > 0
  const canProceedStep2 = description.trim().length >= 10
  const canProceedStep3 = true

  const handleNext = () => {
    if (currentStep < totalSteps) {
      setCurrentStep(currentStep + 1)
    }
  }

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1)
    }
  }

  const handleSubmit = async () => {
    setSubmitting(true)
    setProgress({
      show: true,
      status: 'preparing',
      message: 'Preparing your request...',
      percent: 0,
    })

    try {
      // Upload any remaining pending images
      setProgress((p) => ({ ...p, status: 'uploading', message: 'Uploading images...', percent: 20 }))

      // Create the task
      setProgress((p) => ({ ...p, status: 'generating', message: 'Creating video generation task...', percent: 50 }))

      const payload: CreateTaskPayload = {
        title: description.slice(0, 80),
        product_description: description,
        platform: config.platform,
        style: config.style,
        language: config.language,
        video_length: config.videoLength,
        model: config.model,
        image_urls: imageUrls,
      }

      const task = await createTask(payload)

      setProgress((p) => ({
        ...p,
        status: 'done',
        message: 'Task created successfully!',
        percent: 100,
      }))

      toast.success('Video generation task created!')
      setTimeout(() => {
        router.push(`/dashboard`)
      }, 1500)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to create task'
      setProgress((p) => ({
        ...p,
        status: 'error',
        message,
        percent: 0,
      }))
      toast.error(message)
    } finally {
      setSubmitting(false)
    }
  }

  const isLastStep = currentStep === totalSteps

  const renderStep = () => {
    switch (currentStep) {
      case 1:
        return (
          <div className="space-y-6 animate-fade-in">
            <div className="flex items-center gap-3 mb-2">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500/10">
                <Upload className="h-5 w-5 text-indigo-400" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-white">Upload Product Images</h2>
                <p className="text-sm text-slate-400">
                  Upload images of your product. You can upload up to 10 images.
                </p>
              </div>
            </div>
            <FileUpload onFilesReady={handleImagesReady} maxFiles={10} />
            {imageUrls.length > 0 && (
              <div className="rounded-lg bg-green-500/10 border border-green-500/20 p-3">
                <p className="text-sm text-green-400 font-medium flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4" />
                  {imageUrls.length} image{imageUrls.length > 1 ? 's' : ''} uploaded
                </p>
              </div>
            )}
          </div>
        )

      case 2:
        return (
          <div className="space-y-6 animate-fade-in">
            <div className="flex items-center gap-3 mb-2">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500/10">
                <FileText className="h-5 w-5 text-indigo-400" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-white">Product Description</h2>
                <p className="text-sm text-slate-400">
                  Describe your product in detail. The AI will use this to generate the video.
                </p>
              </div>
            </div>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Enter product description...&#10;&#10;Example: Our wireless earbuds feature active noise cancellation, 24-hour battery life, and a comfortable ergonomic design. Perfect for commuting and workouts."
              className="input-field min-h-[200px] resize-y"
              rows={8}
            />
            <div className="flex items-center justify-between text-xs">
              <span className={description.length >= 10 ? 'text-green-400' : 'text-slate-500'}>
                {description.length} characters
              </span>
              {description.length > 0 && description.length < 10 && (
                <span className="text-yellow-400">Minimum 10 characters required</span>
              )}
            </div>

            {/* Preview */}
            {description.trim().length > 0 && (
              <div className="glass-card p-4">
                <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">Preview</p>
                <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">
                  {description}
                </p>
              </div>
            )}
          </div>
        )

      case 3:
        return (
          <div className="space-y-6 animate-fade-in">
            <div className="flex items-center gap-3 mb-2">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500/10">
                <Settings2 className="h-5 w-5 text-indigo-400" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-white">Configure Video</h2>
                <p className="text-sm text-slate-400">
                  Customize your video settings for the best results.
                </p>
              </div>
            </div>
            <ConfigPanel values={config} onChange={setConfig} />
          </div>
        )

      case 4:
        return (
          <div className="space-y-6 animate-fade-in">
            <div className="flex items-center gap-3 mb-2">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500/10">
                <Eye className="h-5 w-5 text-indigo-400" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-white">Review & Submit</h2>
                <p className="text-sm text-slate-400">
                  Review your settings and submit for generation.
                </p>
              </div>
            </div>

            {/* Summary cards */}
            <div className="grid gap-4">
              {/* Images */}
              <div className="glass-card p-4">
                <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">Images</p>
                <div className="flex flex-wrap gap-2">
                  {imageUrls.slice(0, 4).map((url, i) => (
                    <div key={i} className="h-16 w-16 rounded-lg bg-slate-700 overflow-hidden border border-slate-600">
                      <img src={url} alt="" className="h-full w-full object-cover" />
                    </div>
                  ))}
                  {imageUrls.length > 4 && (
                    <div className="h-16 w-16 rounded-lg bg-slate-700 flex items-center justify-center border border-slate-600">
                      <span className="text-xs text-slate-400">+{imageUrls.length - 4}</span>
                    </div>
                  )}
                </div>
                <p className="text-xs text-slate-500 mt-2">{imageUrls.length} image(s)</p>
              </div>

              {/* Description */}
              <div className="glass-card p-4">
                <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">Description</p>
                <p className="text-sm text-slate-300 line-clamp-3">{description}</p>
              </div>

              {/* Configuration */}
              <div className="glass-card p-4">
                <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">Configuration</p>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-slate-500">Platform</p>
                    <p className="text-slate-200 font-medium capitalize">{config.platform}</p>
                  </div>
                  <div>
                    <p className="text-slate-500">Style</p>
                    <p className="text-slate-200 font-medium capitalize">{config.style}</p>
                  </div>
                  <div>
                    <p className="text-slate-500">Language</p>
                    <p className="text-slate-200 font-medium uppercase">{config.language}</p>
                  </div>
                  <div>
                    <p className="text-slate-500">Length</p>
                    <p className="text-slate-200 font-medium">{config.videoLength}s</p>
                  </div>
                  <div>
                    <p className="text-slate-500">Model</p>
                    <p className="text-slate-200 font-medium capitalize">{config.model}</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Progress overlay */}
            {progress.show && (
              <div className="glass-card p-6 border-indigo-500/30">
                <div className="flex items-center gap-3 mb-4">
                  {progress.status === 'done' ? (
                    <CheckCircle2 className="h-6 w-6 text-green-400" />
                  ) : progress.status === 'error' ? (
                    <AlertCircle className="h-6 w-6 text-red-400" />
                  ) : (
                    <Loader2 className="h-6 w-6 text-indigo-400 animate-spin" />
                  )}
                  <div>
                    <p className="text-sm font-medium text-slate-200">{progress.message}</p>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {progress.status === 'done'
                        ? 'Task created successfully'
                        : progress.status === 'error'
                        ? 'Something went wrong'
                        : 'Please wait...'}
                    </p>
                  </div>
                </div>
                {progress.status !== 'done' && progress.status !== 'error' && (
                  <div className="h-2 rounded-full bg-slate-700 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 transition-all duration-500"
                      style={{ width: `${progress.percent}%` }}
                    />
                  </div>
                )}
              </div>
            )}
          </div>
        )

      default:
        return null
    }
  }

  return (
    <div className="p-6 lg:p-8 max-w-4xl mx-auto animate-fade-in">
      {/* Page Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Create Video</h1>
        <p className="text-sm text-slate-400 mt-1">
          Follow the steps below to generate your AI-powered product video
        </p>
      </div>

      {/* Step Indicator */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          {steps.map((step, index) => (
            <div key={step.id} className="flex items-center flex-1">
              <div className="flex flex-col items-center">
                <div
                  className={`flex h-10 w-10 items-center justify-center rounded-full transition-all duration-300 ${
                    currentStep > step.id
                      ? 'bg-green-500 text-white'
                      : currentStep === step.id
                      ? 'bg-indigo-500 text-white ring-2 ring-indigo-500/30'
                      : 'bg-slate-800 text-slate-500 border border-slate-700'
                  }`}
                >
                  {currentStep > step.id ? (
                    <Check className="h-5 w-5" />
                  ) : (
                    <step.icon className="h-5 w-5" />
                  )}
                </div>
                <p
                  className={`text-xs mt-2 hidden sm:block ${
                    currentStep >= step.id ? 'text-slate-200 font-medium' : 'text-slate-500'
                  }`}
                >
                  {step.title}
                </p>
              </div>
              {index < steps.length - 1 && (
                <div
                  className={`flex-1 h-0.5 mx-3 mt-[-1.5rem] sm:mt-[-2rem] transition-colors duration-300 ${
                    currentStep > step.id ? 'bg-green-500' : 'bg-slate-700'
                  }`}
                />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Step Content */}
      <div className="glass-card p-6 lg:p-8 min-h-[400px]">
        {renderStep()}
      </div>

      {/* Navigation Buttons */}
      <div className="flex items-center justify-between mt-8">
        <button
          onClick={handleBack}
          disabled={currentStep === 1 || submitting}
          className="btn-secondary"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </button>

        {isLastStep ? (
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="btn-primary"
          >
            {submitting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Creating...
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                Generate Video
              </>
            )}
          </button>
        ) : (
          <button
            onClick={handleNext}
            disabled={
              (currentStep === 1 && !canProceedStep1) ||
              (currentStep === 2 && !canProceedStep2) ||
              (currentStep === 3 && !canProceedStep3) ||
              submitting
            }
            className="btn-primary"
          >
            Next
            <ArrowRight className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  )
}
