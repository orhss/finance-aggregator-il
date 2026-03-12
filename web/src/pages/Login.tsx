import React, { useState } from 'react'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'
import { Navigate } from 'react-router-dom'
import { useLogin } from '@/api/auth'
import { useAuth } from '@/contexts/AuthContext'

export default function Login() {
  const { isAuthenticated, setTokens } = useAuth()
  const { mutate: login, isPending, error } = useLogin()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  if (isAuthenticated) return <Navigate to="/dashboard" replace />

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    login(
      { username, password },
      {
        onSuccess: (data) => setTokens(data.access_token, data.refresh_token),
      },
    )
  }

  return (
    <Box
      sx={{
        minHeight: '100dvh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        p: 2,
        background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
      }}
    >
      <Card sx={{ width: '100%', maxWidth: 400 }}>
        <CardContent sx={{ p: 4 }}>
          <Typography variant="h5" fontWeight={800} gutterBottom textAlign="center">
            Fin
          </Typography>
          <Typography variant="body2" color="text.secondary" textAlign="center" gutterBottom>
            Personal Finance Dashboard
          </Typography>

          <Box component="form" onSubmit={handleSubmit} sx={{ mt: 3, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
              fullWidth
            />
            <TextField
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
              fullWidth
            />

            {error && (
              <Typography variant="body2" color="error">
                Invalid credentials. Please try again.
              </Typography>
            )}

            <Button
              type="submit"
              variant="contained"
              size="large"
              disabled={isPending || !username || !password}
              fullWidth
            >
              {isPending ? 'Signing in…' : 'Sign In'}
            </Button>
          </Box>
        </CardContent>
      </Card>
    </Box>
  )
}
