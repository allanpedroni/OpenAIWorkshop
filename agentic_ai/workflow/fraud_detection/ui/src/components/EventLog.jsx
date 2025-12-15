import { useRef, useEffect, Fragment } from 'react';
import {
  Paper,
  Box,
  Typography,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Chip,
  Divider,
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import InfoIcon from '@mui/icons-material/Info';
import GavelIcon from '@mui/icons-material/Gavel';
import ErrorIcon from '@mui/icons-material/Error';
import { getEventIcon, getEventColor, getEventTitle } from '../utils/uiHelpers';
import { formatTime } from '../utils/helpers';

/**
 * Event log component for displaying workflow events in real-time
 * @param {Object} props - Component props
 * @param {Array} props.events - Array of event objects
 */
function EventLog({ events = [] }) {
  const listRef = useRef(null);

  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [events]);

  const icons = { PlayArrowIcon, CheckCircleIcon, InfoIcon, GavelIcon, ErrorIcon };

  return (
    <Paper elevation={3} sx={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <Box sx={{ p: 1.5, borderBottom: 1, borderColor: 'divider', flexShrink: 0 }}>
        <Typography variant="subtitle1" fontWeight="bold">Event Log</Typography>
        <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
          {events.length} events
        </Typography>
      </Box>

      <List
        ref={listRef}
        sx={{
          flex: 1,
          overflow: 'auto',
          px: 0.5,
          py: 0,
          minHeight: 0,
          '&::-webkit-scrollbar': {
            width: '8px',
          },
          '&::-webkit-scrollbar-track': {
            backgroundColor: 'grey.100',
          },
          '&::-webkit-scrollbar-thumb': {
            backgroundColor: 'grey.400',
            borderRadius: '4px',
            '&:hover': {
              backgroundColor: 'grey.600',
            },
          },
        }}
      >
        {events.length === 0 ? (
          <Box sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="caption" color="text.secondary">
              No events yet. Start a workflow to see events.
            </Typography>
          </Box>
        ) : (
          events.map((event, index) => (
            <Fragment key={index}>
              <ListItem
                sx={{
                  py: 0.75,
                  px: 0.75,
                  '&:hover': {
                    bgcolor: 'action.hover',
                  },
                }}
              >
                <ListItemIcon sx={{ minWidth: 32 }}>
                  {getEventIcon(event, icons)}
                </ListItemIcon>
                <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, flexWrap: 'wrap' }}>
                      <Typography variant="caption" fontWeight="medium" sx={{ fontSize: '0.75rem' }}>
                        {getEventTitle(event)}
                      </Typography>
                      <Chip
                        label={event.event_type || event.type}
                        size="small"
                        color={getEventColor(event)}
                        sx={{ height: 16, fontSize: '0.65rem' }}
                      />
                    </Box>
                  }
                  secondary={
                    <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem' }}>
                      {formatTime(event.timestamp)}
                    </Typography>
                  }
                />
              </ListItem>
              {index < events.length - 1 && <Divider variant="inset" component="li" sx={{ ml: 4 }} />}
            </Fragment>
          ))
        )}
      </List>
    </Paper>
  );
}

export default EventLog;
