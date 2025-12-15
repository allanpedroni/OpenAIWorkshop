import React from 'react';
import { Box, Paper, Typography } from '@mui/material';
import ReactMarkdown from 'react-markdown';
import { messageColors } from '../theme/index.js';

/**
 * ChatMessage component - Displays a single chat message
 * @param {object} props
 * @param {object} props.message - Message object with role, content, and timestamp
 */
export const ChatMessage = ({ message }) => {
  const { role, content, timestamp } = message;
  
  const backgroundColor = messageColors[role] || messageColors.assistant;
  const roleLabel = role === 'user' ? 'You' : role === 'error' ? 'Error' : 'Assistant';

  return (
    <Paper
      sx={{
        p: 2,
        mb: 2,
        bgcolor: backgroundColor,
      }}
    >
      <Typography variant="caption" color="text.secondary" gutterBottom display="block">
        {roleLabel} • {timestamp.toLocaleTimeString()}
      </Typography>
      <ReactMarkdown>{content}</ReactMarkdown>
    </Paper>
  );
};
