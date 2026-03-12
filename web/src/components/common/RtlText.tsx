import React from 'react'
import Box from '@mui/material/Box'
import { textDir } from '@/utils/rtl'

interface RtlTextProps {
  text: string
  component?: React.ElementType
  sx?: object
}

/** Renders text with automatic RTL direction detection for Hebrew. */
export function RtlText({ text, component = 'span', sx }: RtlTextProps) {
  const dir = textDir(text)
  return (
    <Box component={component} dir={dir} sx={{ unicodeBidi: 'embed', ...sx }}>
      {text}
    </Box>
  )
}
