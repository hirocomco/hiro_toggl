import { Link } from 'react-router-dom'
import { Home, ArrowLeft, Search, AlertCircle } from 'lucide-react'

export default function NotFound() {
  return (
    <div className="min-h-96 flex flex-col items-center justify-center px-4">
      <div className="text-center space-y-6 max-w-md">
        {/* 404 Illustration */}
        <div className="relative">
          <div className="text-8xl font-bold text-gray-200">404</div>
          <div className="absolute inset-0 flex items-center justify-center">
            <AlertCircle className="h-16 w-16 text-gray-400" />
          </div>
        </div>

        {/* Error Message */}
        <div className="space-y-2">
          <h1 className="text-2xl font-bold text-gray-900">Page Not Found</h1>
          <p className="text-gray-600">
            The page you're looking for doesn't exist or has been moved.
          </p>
        </div>

        {/* Navigation Options */}
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link 
              to="/" 
              className="btn btn-primary"
            >
              <Home className="h-4 w-4 mr-2" />
              Go to Dashboard
            </Link>
            <button 
              onClick={() => window.history.back()}
              className="btn btn-outline"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Go Back
            </button>
          </div>

          {/* Common Links */}
          <div className="pt-4 border-t border-gray-200">
            <p className="text-sm text-gray-500 mb-3">Or try these common pages:</p>
            <div className="flex flex-wrap gap-2 justify-center">
              <Link 
                to="/" 
                className="text-sm text-primary-600 hover:text-primary-700 underline"
              >
                Dashboard
              </Link>
              <span className="text-gray-300">•</span>
              <Link 
                to="/admin" 
                className="text-sm text-primary-600 hover:text-primary-700 underline"
              >
                Admin Panel
              </Link>
              <span className="text-gray-300">•</span>
              <Link 
                to="/settings" 
                className="text-sm text-primary-600 hover:text-primary-700 underline"
              >
                Settings
              </Link>
            </div>
          </div>
        </div>

        {/* Help Text */}
        <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-600">
          <div className="flex items-start space-x-2">
            <Search className="h-4 w-4 mt-0.5 text-gray-400" />
            <div>
              <p className="font-medium text-gray-700">Looking for something specific?</p>
              <ul className="mt-2 space-y-1 text-left">
                <li>• Client reports: Go to Dashboard and click "View Details" on any client</li>
                <li>• Member performance: Click on any member name in client reports</li>
                <li>• Rate management: Visit the Admin panel</li>
                <li>• Data sync: Check the Settings page</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}