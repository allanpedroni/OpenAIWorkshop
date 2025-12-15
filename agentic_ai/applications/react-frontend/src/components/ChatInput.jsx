import React from 'react';
import { Box, TextField, IconButton } from '@mui/material';
import { Send as SendIcon } from '@mui/icons-material';

/**
 * ChatInput component - Input area for sending messages
 * @param {object} props
 * @param {string} props.value - Current input value
 * @param {function} props.onChange - Input change handler
 * @param {function} props.onSend - Send button handler
 * @param {function} props.onKeyPress - Key press handler
 * @param {boolean} props.disabled - Whether input is disabled
 * @param {string} props.placeholder - Input placeholder text
 */
export const ChatInput = ({ 
  value, 
  onChange, 
  onSend, 
  onKeyPress, 
  disabled, 
  placeholder 
}) => {
  return (
    <Box sx={{ display: 'flex', gap: 1 }}>
      <TextField
        fullWidth
        multiline
        maxRows={4}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        onKeyPress={onKeyPress}
        disabled={disabled}
      />
      <IconButton
        color="primary"
        onClick={onSend}
        disabled={!value.trim() || disabled}
        sx={{ alignSelf: 'flex-end' }}
      >
        <SendIcon />
      </IconButton>
    </Box>
  );
};
