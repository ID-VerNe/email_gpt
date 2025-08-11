import React from 'react';

export const highlightText = (text, highlight) => {
    if (!highlight || !text) {
        return text;
    }
    const escapedHighlight = highlight.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp(`(${escapedHighlight})`, 'gi');
    return text.split(regex).map((part, index) => 
        regex.test(part) ? <mark key={index}>{part}</mark> : part
    );
};
