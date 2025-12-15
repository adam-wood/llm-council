import { SignedIn, SignedOut, SignIn, UserButton } from '@clerk/clerk-react'
import './AuthWrapper.css'

export function AuthWrapper({ children }) {
  return (
    <>
      <SignedOut>
        <div className="auth-container">
          <div className="auth-branding">
            <h1>LLM Council</h1>
            <p>Your personal board of AI advisors</p>
          </div>
          <SignIn
            routing="hash"
            appearance={{
              elements: {
                rootBox: 'auth-box',
                card: 'auth-card',
              }
            }}
          />
        </div>
      </SignedOut>
      <SignedIn>
        {children}
      </SignedIn>
    </>
  )
}

export function UserMenu() {
  return (
    <div className="user-menu">
      <UserButton
        afterSignOutUrl="/"
        appearance={{
          elements: {
            userButtonAvatarBox: 'user-avatar'
          }
        }}
      />
    </div>
  )
}
