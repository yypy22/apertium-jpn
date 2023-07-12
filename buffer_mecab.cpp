#include <iostream>
#include <string>
#include <sstream>
#include <mecab.h>

void process_text(std::istream& sin, std::ostream& sout) {
    std::string text;
    std::getline(sin, text);
    
    MeCab::Tagger* tagger = MeCab::createTagger("-Owakati");
    std::stringstream buffer;
    std::string tokenized;
    bool in_bracket = false;
    for (char i : text) {
        buffer << i;
        if (i == text.back()){
            std::string token = tagger->parse(buffer.str().c_str());
            token.erase(token.find_last_not_of(" \n\r\t") + 1);
            tokenized += token;
        }
        if (i == '[') {
            std::string temp = buffer.str();
            temp.pop_back();
            buffer.str(temp);
            std::string parsed = tagger->parse(buffer.str().c_str());
            parsed.erase(parsed.find_last_not_of(" \n\r\t") + 1);
            tokenized += parsed;
            buffer.str("");
            buffer.clear();
            in_bracket = true;
        }
        if (in_bracket) {
            tokenized += i;
        }
        if (i == ']') {
            in_bracket = false;
            buffer.str("");
            buffer.clear();
        }
    }
    
    sout << tokenized;
    
    delete tagger;
}

int main() {
    process_text(std::cin, std::cout);
    return 0;
}
