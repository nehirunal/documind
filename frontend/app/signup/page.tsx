'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card } from '@/components/ui/card'
import { FcGoogle } from 'react-icons/fc'
import { Eye, EyeOff, Mail, Lock, Sparkles } from 'lucide-react'
import Link from 'next/link'

export default function SignupPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [rememberMe, setRememberMe] = useState(false)
  const [message, setMessage] = useState('')
  const router = useRouter()

  const handleSignup = async () => {
    if (password !== confirmPassword) {
      setMessage('Passwords do not match.')
      return
    }
    
    const res = await fetch('http://127.0.0.1:8000/auth/signup', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    })
    
    if (res.ok) {
      const data = await res.json()
      setMessage('Signup successful!')
      router.push('/login')
    } else {
      setMessage('Signup failed!')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100 p-4">
      {/* Logo Section - Outside Card */}
      <div className="w-full max-w-md">
        <div className="text-center mb-6">
          <div className="inline-flex items-center gap-3 mb-4">
            <div className="w-12 h-12 bg-gradient-to-br from-red-500 to-orange-500 rounded-2xl flex items-center justify-center">
              <Sparkles className="w-7 h-7 text-white" />
            </div>
            <h1 className="text-3xl font-bold text-slate-900">
              Newsly<span className="text-orange-500">.AI</span>
            </h1>
          </div>
          <p className="text-slate-600">AI-powered newsletter insights</p>
        </div>

        <Card className="bg-white shadow-xl rounded-2xl p-8 border-0">
          {/* Welcome Text */}
          <div className="text-center mb-6">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Join the future</h2>
            <p className="text-gray-600 text-sm mb-1">Transform overwhelming newsletters into</p>
            <p className="text-gray-600 text-sm">personalized AI insights ✨</p>
          </div>

        {/* Google Sign Up Button */}
        <button className="flex items-center justify-center w-full gap-3 border border-gray-200 rounded-xl py-3 text-sm font-medium text-gray-700 hover:bg-gray-50 mb-6 transition-all duration-200">
          <FcGoogle className="text-xl" /> 
          Continue with Google
        </button>

        {/* Divider */}
        <div className="relative text-center text-gray-400 mb-6">
          <span className="bg-white px-4 relative z-10 text-sm">or sign up with email</span>
          <hr className="absolute top-1/2 left-0 w-full border-gray-200 z-0" />
        </div>

        {/* Form */}
        <div className="space-y-4">
          {/* Email Input */}
          <div className="relative">
            <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400">
              <Mail className="w-4 h-4" />
            </div>
            <Input
              type="email"
              placeholder="Enter your email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="pl-10 h-12 border-gray-200 rounded-xl focus:border-orange-500 focus:ring-orange-500"
            />
          </div>

          {/* Password Input */}
          <div className="relative">
            <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400">
              <Lock className="w-4 h-4" />
            </div>
            <Input
              type={showPassword ? "text" : "password"}
              placeholder="Create password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="pl-10 pr-10 h-12 border-gray-200 rounded-xl focus:border-orange-500 focus:ring-orange-500"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>

          {/* Confirm Password Input */}
          <div className="relative">
            <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400">
              <Lock className="w-4 h-4" />
            </div>
            <Input
              type={showConfirmPassword ? "text" : "password"}
              placeholder="Confirm password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="pl-10 pr-10 h-12 border-gray-200 rounded-xl focus:border-orange-500 focus:ring-orange-500"
            />
            <button
              type="button"
              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>

          {/* Terms Agreement */}
          <div className="flex items-center text-sm">
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="w-4 h-4 text-orange-500 border-gray-300 rounded focus:ring-orange-500"
              />
              <span className="text-gray-600">I agree to terms & conditions</span>
            </label>
          </div>

          {/* Sign Up Button */}
          <Button
            onClick={handleSignup}
            className="w-full h-12 bg-gradient-to-r from-pink-500 to-purple-500 hover:from-pink-600 hover:to-purple-600 text-white font-semibold rounded-xl transition-all duration-200 shadow-lg"
          >
            Sign Up →
          </Button>
        </div>

        {/* Error/Success Message */}
        {message && (
          <p className={`text-center text-sm mt-4 transition-all duration-150 ${
            message.includes('successful') ? 'text-green-600' : 'text-red-500'
          }`}>
            {message}
          </p>
        )}

        {/* Sign In Link */}
        <p className="mt-6 text-sm text-center text-gray-600">
          Already have an account?{' '}
          <Link href="/login" className="text-orange-500 hover:text-orange-600 font-medium hover:underline transition-colors">
            Sign in
          </Link>
        </p>
        </Card>
      </div>
    </div>
  )
}