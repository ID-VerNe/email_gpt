import React, { useState, useRef } from 'react';
import './SearchBar.css';
import { highlightText } from '../utils/highlightText';

const SearchBar = ({ query, setQuery, searchResults, onSelectEmail, isSearching, onImmediateSearch }) => {
    const [suggestions, setSuggestions] = useState([]);
    const [isFocused, setIsFocused] = useState(false);
    const inputRef = useRef(null);
    const searchPrefixes = [
        { prefix: '/from:', description: '按发件人搜索' },
        { prefix: '/subject:', description: '按主题搜索' },
        { prefix: '/body:', description: '按正文搜索' },
        { prefix: '/analysis:', description: '按分析内容搜索' },
        { prefix: '/starred', description: '只看星标邮件' },
    ];

    const handleInputChange = (e) => {
        const value = e.target.value;
        setQuery(value);

        if (value.startsWith('/')) {
            const inputPrefix = value.split(':')[0].toLowerCase();
            const matchingPrefixes = searchPrefixes.filter(p => p.prefix.toLowerCase().startsWith(inputPrefix));
            setSuggestions(matchingPrefixes);
        } else {
            setSuggestions([]);
        }
    };

    const handleFocus = () => {
        setIsFocused(true);
        if (!query) {
            setSuggestions(searchPrefixes);
        }
    };

    const handleSuggestionClick = (prefix) => {
        setQuery(prefix);
        setSuggestions([]);
        inputRef.current.focus();
        if (!prefix.endsWith(':')) {
            onImmediateSearch(prefix);
        }
    };

    const handleEmailSelect = (email) => {
        onSelectEmail(email);
        setIsFocused(false);
    };
    
    const getHighlightTerm = () => {
        if (!query || query === '/starred') return '';
        const parts = query.split(':');
        return parts.length > 1 ? parts.slice(1).join(':') : parts[0];
    };
    const highlightTerm = getHighlightTerm();

    return (
        <div className="search-bar-container" onBlur={() => setTimeout(() => setIsFocused(false), 200)}>
            <input
                ref={inputRef}
                type="text"
                className="search-input"
                placeholder="搜索邮件... (点击查看快捷指令)"
                value={query}
                onChange={handleInputChange}
                onFocus={handleFocus}
                onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        onImmediateSearch(query);
                        inputRef.current.blur();
                    }
                }}
            />
            {isFocused && (
                <ul className="search-results-list">
                    {isSearching ? (
                        <li className="search-info-li">正在搜索...</li>
                    ) : (query && searchResults.length > 0) ? (
                        searchResults.map(email => (
                            <li key={email.id} onMouseDown={() => handleEmailSelect(email)}>
                                <div className="search-result-subject">{highlightText(email.subject, highlightTerm)}</div>
                                <div className="search-result-from">{highlightText(email.from_name || email.from_email, highlightTerm)}</div>
                            </li>
                        ))
                    ) : (suggestions.length > 0) ? (
                        suggestions.map(s => (
                            <li key={s.prefix} onMouseDown={() => handleSuggestionClick(s.prefix)} className="suggestion-li">
                                <strong>{s.prefix}</strong> - {s.description}
                            </li>
                        ))
                    ) : (query && !isSearching) ? (
                        <li className="search-info-li">没有找到匹配的邮件。</li>
                    ) : null}
                </ul>
            )}
        </div>
    );
};

export default SearchBar;
