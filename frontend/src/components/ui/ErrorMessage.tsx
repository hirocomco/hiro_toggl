import { AlertTriangle, RefreshCw } from 'lucide-react'

interface ErrorMessageProps {
  title?: string
  message: string
  onRetry?: () => void
  className?: string
}

export default function ErrorMessage({ 
  title = 'Something went wrong',
  message,
  onRetry,
  className = ''
}: ErrorMessageProps) {
  return (
    <div className={`card ${className}`}>
      <div className="card-body text-center py-8">
        <div className="flex justify-center mb-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-danger-100">
            <AlertTriangle className="h-6 w-6 text-danger-600" />
          </div>
        </div>
        
        <h3 className="text-lg font-semibold text-gray-900 mb-2">
          {title}
        </h3>
        
        <p className="text-gray-600 mb-6 max-w-md mx-auto">
          {message}
        </p>
        
        {onRetry && (
          <button 
            onClick={onRetry}
            className="btn btn-outline btn-sm"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Try Again
          </button>
        )}
      </div>
    </div>
  )
}