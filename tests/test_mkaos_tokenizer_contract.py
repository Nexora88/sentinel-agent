from core.mkaos_tokenizer_contract import (
    CONTRACT_ID, EOS_ID, VOCAB_SIZE, decode_tokens, encode_documents,
    encode_text, load_golden_vectors,
)


def test_shared_golden_vectors_match_byte_for_byte():
    for _name, text, expected in load_golden_vectors():
        assert encode_text(text) == expected
        assert decode_tokens(expected) == text


def test_contract_special_token_and_document_boundary():
    assert CONTRACT_ID == "mkaos-byte-v1"
    assert VOCAB_SIZE == 257
    assert EOS_ID == 256
    assert encode_documents(["A", "ş"]) == [65, EOS_ID, *"ş".encode("utf-8"), EOS_ID]


def test_dotted_and_dotless_i_are_not_normalized():
    assert encode_text("I") != encode_text("ı")
    assert encode_text("İ") != encode_text("i")


def test_decoder_rejects_out_of_range_token():
    import pytest
    with pytest.raises(ValueError):
        decode_tokens([257])
