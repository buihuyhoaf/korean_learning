-- Fix PostgreSQL sequences to avoid ID conflicts
-- Run this script BEFORE running entry_test_data.sql

-- Check and update entry_test_questions sequence
DO $$
DECLARE
    max_id INTEGER;
    seq_exists BOOLEAN;
BEGIN
    -- Get max ID from table
    SELECT COALESCE(MAX(id), 0) INTO max_id FROM entry_test_questions;
    
    -- Check if sequence exists and get its current value
    SELECT EXISTS (
        SELECT 1 FROM information_schema.sequences 
        WHERE sequence_name = 'entry_test_questions_id_seq'
    ) INTO seq_exists;
    
    IF seq_exists THEN
        -- Update sequence to be at least max_id + 1
        PERFORM setval('entry_test_questions_id_seq', GREATEST(max_id + 1, nextval('entry_test_questions_id_seq')));
        RAISE NOTICE 'Updated entry_test_questions_id_seq: max_id=%, sequence now at %', max_id, currval('entry_test_questions_id_seq');
    ELSE
        RAISE NOTICE 'Sequence entry_test_questions_id_seq not found - will use default auto-increment';
    END IF;
END $$;

-- Check and update entry_test_question_options sequence  
DO $$
DECLARE
    max_id INTEGER;
    seq_exists BOOLEAN;
BEGIN
    -- Get max ID from table
    SELECT COALESCE(MAX(id), 0) INTO max_id FROM entry_test_question_options;
    
    -- Check if sequence exists
    SELECT EXISTS (
        SELECT 1 FROM information_schema.sequences 
        WHERE sequence_name = 'entry_test_question_options_id_seq'
    ) INTO seq_exists;
    
    IF seq_exists THEN
        -- Update sequence to be at least max_id + 1
        PERFORM setval('entry_test_question_options_id_seq', GREATEST(max_id + 1, nextval('entry_test_question_options_id_seq')));
        RAISE NOTICE 'Updated entry_test_question_options_id_seq: max_id=%, sequence now at %', max_id, currval('entry_test_question_options_id_seq');
    ELSE
        RAISE NOTICE 'Sequence entry_test_question_options_id_seq not found - will use default auto-increment';
    END IF;
END $$;
