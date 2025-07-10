import { clsx } from 'clsx'

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  className?: string
  text?: string
}

export default function LoadingSpinner({ 
  size = 'md', 
  className,
  text 
}: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-6 w-6',
    lg: 'h-8 w-8'
  }

  return (
    <div className={clsx('flex items-center justify-center', className)}>
      <div className="flex flex-col items-center space-y-2">
        <div className={clsx('loading-spinner', sizeClasses[size])} />
        {text && (
          <p className="text-sm text-gray-500">{text}</p>
        )}
      </div>
    </div>
  )
}