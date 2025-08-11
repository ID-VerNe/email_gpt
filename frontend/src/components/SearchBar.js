import React, { useState, useRef } from 'react';
import './SearchBar.css';
import { highlightText } from '../utils/highlightText';

const SearchBar = ({ query, setQuery, searchResults, onSelectEmail, isSearching }) => {
    const [suggestions, setSuggestions] = useState([]);
    const [isFocused, setIsFocused] = useState(false);
    const inputRef = useRef(null);
    const searchPrefixes = [
        { prefix: '/from:', description: '按发件人搜索' },
        { prefix: '/subject:', description: '按主题搜索' },
        { prefix: '/body:', description: '按正文搜索' },
        { prefix: '/analysis:', description: '按分析内容搜索' },
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

    const handleSuggestionClick = (prefix) => {
        setQuery(prefix);
        setSuggestions([]);
        inputRef.current.focus();
    };

    const handleEmailSelect = (email) => {
        onSelectEmail(email);
        setIsFocused(false); // Hide results on selection
    };
    
    const getHighlightTerm = () => {
        if (!query) return '';
        const parts = query.split(':');
        return parts.length > 1 ? parts.slice(1).join(':') : parts[0];
    };
    const highlightTerm = getHighlightTerm();

    return (
        <div className="search-bar-container" onFocus={() => setIsFocused(true)} onBlur={() => setTimeout(() => setIsFocused(false), 200)}>
            <input
                ref={inputRef}
                type="text"
                className="search-input"
                placeholder="搜索邮件... (按 Enter 确认, 使用 /from: 等进行字段搜索)"
                value={query}
                onChange={handleInputChange}
                onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                    }
                }}
            />
            {isFocused && query && (
                <ul className="search-results-list">
                    {isSearching ? (
                        <li className="search-info-li">正在搜索...</li>
                    ) : suggestions.length > 0 ? (
                        suggestions.map(s => (
                            <li key={s.prefix} onMouseDown={() => handleSuggestionClick(s.prefix)} className="suggestion-li">
                                <strong>{s.prefix}</strong> - {s.description}
                            </li>
                        ))
                    ) : searchResults.length > 0 ? (
                        searchResults.map(email => (
                            <li key={email.id} onMouseDown={() => handleEmailSelect(email)}>
                                <div className="search-result-subject">{highlightText(email.subject, highlightTerm)}</div>
                                <div className="search-result-from">{highlightText(email.from_name || email.from_email, highlightTerm)}</div>
                            </li>
                        ))
                    ) : (
                        <li className="search-info-li">没有找到匹配的邮件。</li>
                    )}
                </ul>
            )}
        </div>
    );
};

export default SearchBar;
