from typing import List

def chunk_text(text: str, max_chars: int = 4000, overlap: int = 400) -> List[str]:
    if not text:
        return []
        
    chunks = []
    lines = text.splitlines(keepends=True)
    current_chunk = []
    current_size = 0
    
    for line in lines:
        line_len = len(line)
        if current_size + line_len > max_chars:
            if current_chunk:
                chunks.append("".join(current_chunk))
            # Add overlap to the next chunk
            overlap_chars = 0
            overlap_lines = []
            if current_chunk:
                for rev_line in reversed(current_chunk):
                    if overlap_chars + len(rev_line) <= overlap:
                        overlap_lines.insert(0, rev_line)
                        overlap_chars += len(rev_line)
                    else:
                        break
            current_chunk = overlap_lines + [line]
            current_size = sum(len(l) for l in current_chunk)
        else:
            current_chunk.append(line)
            current_size += line_len
            
    if current_chunk:
        chunks.append("".join(current_chunk))
        
    return chunks