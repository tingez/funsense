from pydantic import BaseModel, field_serializer
from typing import Dict, List, Optional, Set
import json
import os
import tiktoken

class LabelNode(BaseModel):
    name: str
    parent: Optional[str] = None
    children: List[str] = []
    email_ids: Set[str] = set()

    @field_serializer('email_ids')
    def serialize_email_ids(self, email_ids: Set[str], _info):
        return list(email_ids)

class LabelHierarchy:
    """Manages a hierarchical label structure for organizing email content.
    
    The hierarchy is built from filenames in the format: parent_child_grandchild_*.json
    For example:
    - LLM_RAG_evaluation_20241222.json creates the hierarchy: LLM -> RAG -> evaluation
    - LLM_paper_20241222.json creates: LLM -> paper
    
    Special cases:
    - Single labels like 'good_material' and 'daily_news' are treated as root nodes
    - Each node stores its parent, children, and associated email IDs
    - Email IDs are propagated up the hierarchy (parent nodes contain all child email IDs)
    - Each label has a path to root that preserves the hierarchical relationship
    """
    def __init__(self):
        self.nodes: Dict[str, LabelNode] = {}  # Map of label name to node
        self.root_labels: List[str] = []  # Labels with no parent
        self.single_labels = {'good_material', 'daily_news'}  # Labels that should not be split

    def add_label_from_filename(self, filename: str, email_ids: List[str]):
        """Add labels from filename like 'LLM_RAG_evaluation_20241222_220726.json'"""
        parts = os.path.basename(filename).split('_')
        current_parent = None
        
        # Skip datetime part at the end
        label_parts = []
        for part in parts:
            if not part[0].isdigit():  # Skip parts starting with numbers (datetime)
                label_parts.append(part)

        # Check for special case single labels
        combined_label = '_'.join(label_parts[:2]).split('.')[0]  # Join first two parts and remove .json
        if combined_label in self.single_labels:
            if combined_label not in self.nodes:
                self.nodes[combined_label] = LabelNode(
                    name=combined_label,
                    parent=None,
                    children=[],
                    email_ids=set(email_ids)
                )
                self.root_labels.append(combined_label)
            else:
                self.nodes[combined_label].email_ids.update(email_ids)
            return
        
        # Process each label part for hierarchical labels
        current_path = []  # Keep track of the current path
        for part in label_parts:
            clean_part = part.split('.')[0]  # Remove .json if present
            current_path.append(clean_part)
            
            if clean_part not in self.nodes:
                self.nodes[clean_part] = LabelNode(
                    name=clean_part,
                    parent=current_parent,
                    children=[],
                    email_ids=set()
                )
                if current_parent:
                    if clean_part not in self.nodes[current_parent].children:
                        self.nodes[current_parent].children.append(clean_part)
                else:
                    if clean_part not in self.root_labels:
                        self.root_labels.append(clean_part)
            
            # Add email IDs to all nodes in the path
            # This ensures that parent nodes also get the email IDs
            for path_label in current_path:
                self.nodes[path_label].email_ids.update(email_ids)
            
            current_parent = clean_part

    def get_path_to_root(self, label: str) -> List[str]:
        """Get the path from a label to root"""
        if label not in self.nodes:
            return []
        path = [label]
        current = self.nodes[label]
        while current.parent:
            path.append(current.parent)
            current = self.nodes[current.parent]
        return list(reversed(path))

    def get_all_paths_for_email(self, email_id: str) -> List[List[str]]:
        """Get all hierarchical paths for an email ID"""
        paths = []
        # First collect all labels that have this email
        labels_with_email = [
            label for label, node in self.nodes.items() 
            if email_id in node.email_ids
        ]
        
        # For each label, get its path to root
        for label in labels_with_email:
            path = self.get_path_to_root(label)
            if path and path not in paths:  # Only add unique paths
                paths.append(path)
                
                # If this is a leaf node, also add paths for all its ancestors
                current = self.nodes[label]
                while current.parent:
                    parent_path = self.get_path_to_root(current.parent)
                    if parent_path and parent_path not in paths:
                        paths.append(parent_path)
                    current = self.nodes[current.parent]
        
        return paths

    def to_dict(self) -> dict:
        """Convert hierarchy to dictionary for serialization"""
        return {
            "nodes": {k: v.model_dump() for k, v in self.nodes.items()},
            "root_labels": self.root_labels
        }

class FewShotExample(BaseModel):
    content: str
    labels: List[str]
    label_paths: List[List[str]]

class FewShotDataset:
    def __init__(self, hierarchy: LabelHierarchy, analyzed_data: Dict):
        self.hierarchy = hierarchy
        self.analyzed_data = analyzed_data
        self.examples: List[FewShotExample] = []
        self.label_examples: Dict[str, List[FewShotExample]] = {}
        self.tokenizer = tiktoken.get_encoding("cl100k_base")  # GPT-4 tokenizer
        self.MAX_TOKENS = 32000  # Leave some room for system prompt and user query

    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in a text string"""
        return len(self.tokenizer.encode(text))

    def estimate_example_tokens(self, example: FewShotExample) -> int:
        """Estimate the number of tokens an example will use in the prompt"""
        formatted = self.format_example(example)
        return self.count_tokens(formatted)

    def generate_examples(self, min_examples_per_label: int = 1, max_examples_per_label: Optional[int] = None):
        """
        Generate examples from the hierarchy and analyzed data.
        Ensures balanced representation of labels and minimum examples per label.
        Also ensures the total token count stays under MAX_TOKENS.
        
        Args:
            min_examples_per_label: Minimum number of examples per label
            max_examples_per_label: Maximum number of examples per label. If None, will be calculated
                                  to ensure balanced representation.
        """
        # Initialize label examples dictionary
        for label in self.hierarchy.nodes:
            self.label_examples[label] = []

        # First pass: collect all possible examples for each label
        for label in self.hierarchy.nodes:
            node = self.hierarchy.nodes[label]
            valid_examples = []
            
            for email_id in node.email_ids:
                if email_id in self.analyzed_data:
                    email_data = self.analyzed_data[email_id]
                    content = email_data.get('post_content_en', '')
                    if content:
                        # Get all hierarchical paths for this email
                        label_paths = self.hierarchy.get_all_paths_for_email(email_id)
                        # Get unique labels from paths
                        labels = list({path[-1] for path in label_paths})
                        
                        example = FewShotExample(
                            content=content,
                            labels=labels,
                            label_paths=label_paths
                        )
                        
                        # Only add if it's not too long by itself
                        tokens = self.estimate_example_tokens(example)
                        if tokens <= self.MAX_TOKENS // 2:  # Single example shouldn't use more than half the context
                            valid_examples.append((example, tokens))
                        
            self.label_examples[label].extend(valid_examples)

        # Calculate balanced number of examples per label
        if max_examples_per_label is None:
            # Find the label with minimum number of examples (but at least min_examples_per_label)
            min_available = max(
                min_examples_per_label,
                min(len(examples) for examples in self.label_examples.values())
            )
            max_examples_per_label = min_available

        # Second pass: select balanced examples while tracking token count
        self.examples = []
        examples_added = set()  # Track unique examples by content
        total_tokens = self.count_tokens("Here are some examples of content and their hierarchical labels:\n\n")
        total_tokens += self.count_tokens("\nNow, please analyze the following content and assign appropriate hierarchical labels:\n\n")

        # Sort labels by number of available examples (ascending)
        sorted_labels = sorted(
            self.label_examples.keys(),
            key=lambda x: len(self.label_examples[x])
        )

        # First ensure minimum examples for each label
        for label in sorted_labels:
            examples = self.label_examples[label]
            if not examples:
                print(f"Warning: No examples found for label '{label}'")
                continue
                
            # Shuffle examples to get random selection
            import random
            random.shuffle(examples)
            
            # Add examples up to min_examples_per_label
            added_count = 0
            for example, tokens in examples:
                if added_count >= min_examples_per_label:
                    break
                    
                # Check if adding this example would exceed token limit
                if total_tokens + tokens > self.MAX_TOKENS:
                    print(f"Warning: Reached token limit ({self.MAX_TOKENS}). Stopping example generation.")
                    break
                    
                # Only add if we haven't added this content before
                if example.content not in examples_added:
                    self.examples.append(example)
                    examples_added.add(example.content)
                    total_tokens += tokens
                    added_count += 1

        # Then add more examples up to max_examples_per_label if space allows
        if total_tokens < self.MAX_TOKENS:
            for label in sorted_labels:
                examples = self.label_examples[label]
                added_count = sum(1 for ex in self.examples if label in ex.labels)
                
                for example, tokens in examples:
                    if added_count >= max_examples_per_label:
                        break
                        
                    # Check token limit
                    if total_tokens + tokens > self.MAX_TOKENS:
                        print(f"Warning: Reached token limit ({self.MAX_TOKENS}). Stopping example generation.")
                        break
                        
                    # Only add if we haven't added this content before
                    if example.content not in examples_added:
                        self.examples.append(example)
                        examples_added.add(example.content)
                        total_tokens += tokens
                        added_count += 1

        print(f"\nExample distribution by label:")
        for label in sorted(self.label_examples.keys()):
            count = sum(1 for ex in self.examples if label in ex.labels)
            print(f"{label}: {count} examples")
        print(f"Total tokens: {total_tokens} / {self.MAX_TOKENS}")

    def format_example(self, example: FewShotExample) -> str:
        """Format a single example for few-shot learning"""
        formatted = f"Content: {example.content}\n"
        formatted += "Labels:\n"
        for label, path in zip(example.labels, example.label_paths):
            if label in self.hierarchy.single_labels:
                formatted += f"- {label}\n"  # Single label without hierarchy
            else:
                formatted += f"- {' -> '.join(path)}\n"  # Hierarchical path
        return formatted

    def generate_prompt(self, num_examples: int = 5) -> str:
        """Generate a few-shot learning prompt with specified number of examples"""
        if not self.examples:
            raise ValueError("No examples generated. Call generate_examples() first.")
            
        # Ensure we have enough examples
        if num_examples > len(self.examples):
            print(f"Warning: Requested {num_examples} examples but only {len(self.examples)} available.")
            num_examples = len(self.examples)
        
        # Shuffle examples to get a random selection
        import random
        selected_examples = random.sample(self.examples, num_examples)
        
        # Calculate total tokens
        prompt = "Here are some examples of content and their hierarchical labels:\n\n"
        total_tokens = self.count_tokens(prompt)
        
        for example in selected_examples:
            example_text = self.format_example(example) + "\n---\n\n"
            example_tokens = self.count_tokens(example_text)
            if total_tokens + example_tokens > self.MAX_TOKENS:
                print(f"Warning: Stopping at {len(prompt.split('---')) - 1} examples to stay within token limit")
                break
            prompt += example_text
            total_tokens += example_tokens
            
        prompt += "Now, please analyze the following content and assign appropriate hierarchical labels:\n\n"
        total_tokens = self.count_tokens(prompt)
        print(f"Final prompt tokens: {total_tokens} / {self.MAX_TOKENS}")
        return prompt

def build_label_hierarchy(dumps_dir: str) -> LabelHierarchy:
    """Build label hierarchy from email dumps directory"""
    hierarchy = LabelHierarchy()
    
    for filename in os.listdir(dumps_dir):
        if filename.endswith('.json'):
            filepath = os.path.join(dumps_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        email_ids = [item['id'] for item in data]
                    else:
                        email_ids = [data['id']]
                    hierarchy.add_label_from_filename(filename, email_ids)
            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")
                traceback.print_exc()
    
    return hierarchy
